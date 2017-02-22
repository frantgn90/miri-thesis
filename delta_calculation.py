#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Delta is the portion of the execution that has been executed by mean of loops
Could be said that is the portion of the execution of really work. 1-Delta can be
initializations and last treatments of data.
'''

import sys
import numpy,math

from sympy.solvers import solve
from sympy import Symbol

import logging
import constants

_upper_bound=1
_init_delta=0.5

# Delta is bounded by (_bottom_bound, 1)


def getCost(lmbda, T, P, delta):
    return lmbda-((T*delta)/P)

def filter_under_delta(cdist, total_time, delta):
    result = {k:v for k,v in cdist.items() \
                if getCost(\
                    v["times"],\
                    total_time,\
                    v["time_mean"], delta) > 0\
             }
    return result


def filter_by_delta(cdist, total_time, delta):
    result = {k:v for k,v in cdist.items() \
                if getCost(\
                    v["times"],\
                    total_time,\
                    v["time_mean"], delta) == 0\
             }
    return result

def filter_by_delta_range(cdist, total_time, delta_bottom, delta_top):
    result = {k:v for k,v in cdist.items() \
                if getCost(v["times"],\
                        total_time,\
                        v["time_mean"], delta_bottom) > 0 and \
                   getCost(v["times"],\
                        total_time,\
                        v["time_mean"], delta_top) <= 0
             }
    return result


def getDelta(cdist, total_time, bottom_bound):
    cost=sys.maxint
    delta=_init_delta
    optimal=delta

    for delta in numpy.arange(max(bottom_bound,0.01), _upper_bound, 0.01):
        mean_cost=0 
        for cs,data in cdist.items():
            pcost=abs(getCost(data["times"], total_time, data["time_mean"], delta))
            mean_cost+=pcost

        mean_cost/=len(cdist)
        if mean_cost < cost:
            optimal=delta
            cost=mean_cost

    return optimal

def mean_distance_from_delta(data, total_time, delta):
    mean_distance = 0
    if len(data) == 0: return 0

    for k,v in data.items():
        mean_distance = abs(getCost(
                                v["times"],
                                total_time,
                                v["time_mean"],
                                delta))

    return mean_distance/len(data)

def calcule_deltas_heuristic(depured_data, total_time, bottom_bound, epsilon):

    deltas=[]
    delta_step=epsilon
   
    total_callstacks = 0
    for data in depured_data:
        total_callstacks+=len(data)

    total_covered = 0
    while not total_covered == total_callstacks:
        max_covered = 0
        min_mean_distances = sys.maxint
        for current_delta in numpy.arange(0, 1, delta_step):
            calls_covered=0
            mean_distances=0

            for data in depured_data:
                for d in deltas: # Filtering the current covered calls
                    data = {k: v for k, v in data.items() if v["delta"] == None}

                filtered = filter_by_delta_range(
                        data, 
                        total_time, 
                        #current_delta-current_delta*epsilon,
                        #current_delta+current_delta*epsilon)
                        current_delta-epsilon,
                        current_delta+epsilon)
                calls_covered+=len(filtered)

                mean_distances += mean_distance_from_delta(
                        filtered,
                        total_time,
                        current_delta)

            mean_distances/=len(depured_data)
            
            if calls_covered > max_covered or (calls_covered == max_covered \
                        and mean_distances < min_mean_distances):
                max_covered = calls_covered
                optimum_delta = current_delta
                min_mean_distances = mean_distances 

        if max_covered > 0:
            deltas.append(optimum_delta)
            total_covered+=max_covered

            for data in depured_data:
                to_set_delta = filter_by_delta_range(
                        data,
                        total_time,
                        #optimum_delta-optimum_delta*epsilon,
                        #optimum_delta+optimum_delta*epsilon)
                        optimum_delta-epsilon,
                        optimum_delta+epsilon)

                for k,v in to_set_delta.items():
                    data[k]["delta"] = optimum_delta

                    
    
    return deltas

def calcule_deltas_cplex(depured_data, total_time, bottom_bound):
    # For the moment, we want to generate the input CPLEX data file

    big_m=100000
    delta_accuracy = 0.02
    nDeltas = 1/delta_accuracy

    deltas=[]
    for i in numpy.arange(delta_accuracy, 1, delta_accuracy):
        deltas.append(i)

    points=[]
    for cs in depured_data:
        for k,v in cs.items():
            points.append([v[constants._x_axis],v[constants._y_axis]])

    distance_dp = []
    for delta in deltas:
        distance_delta=[]
        for point in points:
            min_distance = get_minimum_distance(delta, total_time, point)
            distance_delta.append(min_distance)


            logging.info("Distances from point ({0},{1}) to delta {2} = {3}"
                    .format(point[0], point[1], delta, min_distance))
        distance_dp.append(distance_delta)

    ff = open("cplex.dat", "w")
    ff.write("bigM={0};\n".format(big_m))
    ff.write("nDeltas={0};\n".format(len(deltas)))
    ff.write("nPoints={0};\n".format(len(points)))
    ff.write("Deltas={0};\n".format(deltas))
    ff.write("Points={0};\n".format(points))
    ff.write("Distance_dp={0};\n".format(distance_dp))
    ff.close()

# Inspired on (last comment): http://math.stackexchange.com/questions/967268/
# finding-the-closest-distance-between-a-point-a-curve
def get_minimum_distance(delta,total_time, point):
    T=delta*total_time
    X=point[0]
    Y=point[1]

    x=Symbol("x",real=True)
    solutions = solve(2*x**4 - 2*X*x**3 + 2*T*Y*x - 2*T**2, x)
    
    # Once we have de solutions we want to get the minimum distance
    min_distance = float("inf")
    for solution in solutions:
        distance = math.sqrt((solution-X)**2 + ((T/solution)-Y)**2)
        if distance < min_distance:
            min_distance = distance

    return min_distance
