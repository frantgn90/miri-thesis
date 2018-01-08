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
import multiprocessing
from multiprocessing import Pool
from sympy.solvers import solve,nsolve
from sympy import Symbol
import logging

import constants
from cplex_interface import CplexInterface
from utilities import ProgressBar


from sklearn.cluster import DBSCAN

_upper_bound=1
_init_delta=0.5

# Delta is bounded by (_bottom_bound, 1)


def get_cost(lmbda, T, P, delta):
    return lmbda-((T*delta)/P)

def filter_under_delta(cdist, total_time, delta):
    result = {k:v for k,v in cdist.items() \
                if get_cost(\
                    v["times"],\
                    total_time,\
                    v["time_mean"], delta) > 0\
             }
    return result


def filter_by_delta(cdist, total_time, delta):
    result = {k:v for k,v in cdist.items() \
                if get_cost(\
                    v["times"],\
                    total_time,\
                    v["time_mean"], delta) == 0\
             }
    return result

def filter_by_delta_range(cdist, total_time, delta_bottom, delta_top):
    result = {k:v for k,v in cdist.items() \
                if get_cost(v["times"],\
                        total_time,\
                        v["time_mean"], delta_bottom) > 0 and \
                   get_cost(v["times"],\
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
            pcost=abs(get_cost(data["times"], total_time, data["time_mean"], delta))
            mean_cost+=pcost

        mean_cost/=len(cdist)
        if mean_cost < cost:
            optimal=delta
            cost=mean_cost

    return optimal


def filter_by_distance(callstacks, total_time, delta, epsilon):
    result = {k:v for k,v in callstacks.items() if get_minimum_distance(
                    delta, total_time, [v["times"],v["time_mean"]]) <= epsilon}

    return result

def get_near_points(data, total_time,  delta, epsilon):
    points = []
    
    for rank_data in data:
        # Filter already categorized data
        rank_data = {k: v for k, v in rank_data.items() if v["delta"] == None}

        filtered = filter_by_distance(rank_data, total_time,  delta, epsilon)

        for key, value in filtered.items():
            points.append([value["times"],value["time_mean"]])

    if len(points) == 0:
        return [], float("inf")

    sum_square_distances=0
    for point in points:
        sum_square_distances += get_minimum_distance(delta, total_time, point)

    mean_square_distances = sum_square_distances/len(points)
    return points, mean_square_distances

def calcule_deltas_clustering(callstacks, total_time):
    data = []
    for cs in callstacks:
        cs.set_private_delta(total_time)
        data.append(cs.private_delta)

    X=numpy.array(data).reshape(-1,1)
    db = DBSCAN(eps=0.2, min_samples=1).fit(X)
    core_samples_mask = numpy.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels=db.labels_


    ndeltas = len(set(labels)) - (1 if -1 in labels else 0)
    unique_labels = list(set(labels))
    grouped_deltas = dict.fromkeys(unique_labels)

    for d,cs in zip(labels, callstacks):
        cs.delta_cluster = d
        if grouped_deltas[d] is None:
            grouped_deltas[d] = [cs.private_delta]
        else:
            grouped_deltas[d].append(cs.private_delta)

    for k in grouped_deltas:
        grouped_deltas[k] = round(numpy.mean(grouped_deltas[k]),2)

    for cs in callstacks:
        cs.delta = grouped_deltas[cs.delta_cluster]

    return grouped_deltas.keys()

def calcule_deltas_heuristic(data, total_time, bottom_bound, epsilon):
    assert False, "Hoy no... mañana!, Execute with --cplex"

def calcule_deltas_cplex(
        fcallstacks_pool, 
        total_time, 
        bottom_bound, 
        delta_accuracy, cplex_input):
    #
    # Preparing data for CPLEX
    #

    npoints = len(fcallstacks_pool)

    if cplex_input == None:
        logging.debug("Preparing data for CPLEX")
        nDeltas = 1/delta_accuracy
        deltas=[]
        for i in numpy.arange(bottom_bound, 1, delta_accuracy):
            deltas.append(i)
        deltas.append(1)

        points=[]
        for cs in fcallstacks_pool:
            points.append([cs.repetitions[cs.rank],cs.instants_distances_mean])

        big_m = 0
        distance_dp = []

        pool = Pool(1)

        for delta in deltas:
            logging.debug("Calculing distances to delta {0}".format(delta))
            pp = zip([delta]*len(points), [total_time]*len(points), points)
            distance_delta = pool.map(get_minimum_distance,pp)
            distance_dp.append(distance_delta) 

            max_dist = max(distance_delta)
            if max_dist > big_m:
                big_m = max_dist

        arguments = {
                constants.OPL_ARG_BIGM:    big_m,
                constants.OPL_ARG_NDELTAS: len(deltas),
                constants.OPL_ARG_NPOINTS: len(points),
                constants.OPL_ARG_DELTAS:  deltas,
                constants.OPL_ARG_POINTS:  points,
                constants.OPL_ARG_DISTDP:  distance_dp}

        cplex_int = CplexInterface()
        infile = cplex_int.set_args(arguments)

        logging.debug("CPLEX infile generated: {0}".format(infile))
    else:
        logging.debug("Using CPLEX input: {0}".format(cplex_input))
        cplex_int = CplexInterface()
        cplex_int.set_infile(cplex_input)

    #
    # Launching CPLEX
    #
    logging.debug("Launching CPLEX for delta clasification...")

    logging.debug("Using CPLEX outfile: {0}".format(cplex_int.get_outfile()))
    logging.debug("Using CPLEX errfile: {0}".format(cplex_int.get_errfile()))

    cplex_int.run()  

    #
    # Update points delta
    #
    logging.debug("Updating points delta clasification...")
    point_cnt = 0
    pbar = ProgressBar("Updating points", npoints)
    pbar.show()

    for cs in fcallstacks_pool:
        cs.delta = cplex_int.get_delta_point_map(point_cnt)
        point_cnt += 1
        pbar.progress_by(1)
        pbar.show()
            
    return cplex_int.get_used_deltas()

# Inspired on (last comment): http://math.stackexchange.com/questions/967268/
# finding-the-closest-distance-between-a-point-a-curve
def get_minimum_distance(arguments):
    delta = arguments[0]
    total_time = arguments[1]
    point = arguments[2]

    T=delta*total_time
    X=point[0]
    Y=point[1]
    a=2; b=-2*X; c=2*T*Y; d=-2*T**2

    x=Symbol("x",real=True)

    #print "================"
    #print "X={0} Y={1} T={2}".format(X,Y,T)
    #print "a={0} b={1} c={2} d={3}".format(a,b,c,d)
    solutions = solve(a*x**4 + b*x**3 + c*x + d, x)
    #print solutions
    #print "================"
    #if len(solutions) == 0:
    #    exit(1)

    # Once we have de solutions we want to get the minimum distance
    min_distance = float("inf")
    min_solution = 0
    for solution in solutions:
        distance = math.sqrt((solution-X)**2 + ((T/solution)-Y)**2)

        if distance < min_distance:
            min_distance = distance
            min_solution = [solution, T/solution]

#    return min_distance, min_solution
    return min_distance**2

def get_minimum_distance_2(delta, total_time, point):
    return _get_minimum_distance_2(delta, total_time, point, 0, 0)

def _get_minimum_distance_2(delta, total_time, point, accumulated, iteration):
    # Calculation of the distance to delta function by mean of approximations
    # using the same technique as whith linear functions but in a recursive way

    X=point[0]
    Y=point[1]

    B=[X,(delta*total_time)/float(X)]
    C=[(delta*total_time)/float(Y),Y]

    is_below=(B[1] > Y)

    b=abs(X-C[0])
    c=abs(Y-B[1])
    a=math.sqrt(b**2+c**2)

    if a==0: 
        return accumulated, point
    if accumulated > 0 and is_below:
        return accumulated, point

    h=(b*c)/a
    h = (-h if is_below else h)
    
    #print "Below={0} : {1}\n".format(is_below, h+accumulated)
    #print "A={0}".format(point)
    #print "B={0}".format(B)
    #print "C={0}".format(C)

    m=(b**2)/a
    n=(c**2)/a

    if not is_below:
        coeff=float(m)/a
        new_point = [C[0]+b*coeff, C[1]-c*coeff]
    else:
        coeff=float(n)/a
        new_point = [B[0]+b*coeff, B[1]-c*(1-coeff)]

    if iteration < constants.MAX_ITERATIONS:
        #print "\nn={0}; m={1}".format(n,m)
        #print "E={0}".format(new_point)
        #print "--------------"

        return _get_minimum_distance_2(
                delta, 
                total_time, 
                new_point, 
                h+accumulated, 
                iteration+1)
    else:
        return abs(h+accumulated), new_point

