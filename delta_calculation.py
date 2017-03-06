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


def filter_by_distance(callstacks, total_time, delta, epsilon):
    result = {k:v for k,v in callstacks.items() \
                if get_minimum_distance(delta, total_time, [v["times"],v["time_mean"]]) <= epsilon}

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


#def calcule_deltas_heuristic(depured_data, total_time, bottom_bound, epsilon):
#    deltas=[]
#    delta_step=epsilon
#   
#    total_callstacks = 0
#    for data in depured_data:
#        total_callstacks+=len(data)
#
#    total_covered = 0
#    while not total_covered == total_callstacks:
#        logging.info("{0}% of points covered with {1} deltas".format(
#            total_covered/total_callstacks*100, len(deltas)))
#
#        max_covered = 0
#        min_mean_distance = sys.maxint
#
#        for current_delta in numpy.arange(0.1, 1, delta_step):
#            near_points, mean_distance = 
#                get_near_points(depured_data, total_time, current_delta, epsilon)
#            calls_covered = len(near_points)
#
#            if calls_covered > max_covered or \
#                (calls_covered == max_covered and mean_distance < min_mean_distance):
#                max_covered = calls_covered
#                optimum_delta = current_delta
#                min_mean_distance = mean_distance
#
#        if max_covered > 0:
#            deltas.append(optimum_delta)
#            total_covered+=max_covered
#
#            for data in depured_data:
#                set_to_delta = filter_by_distance(data, total_time,
#                        optimum_delta,
#                        epsilon)
#
#                for k,v in to_set_delta.items():
#                    data[k]["delta"] = optimum_delta
#
#                    
#    
#    return deltas

def calcule_deltas_heuristic(data, total_time, bottom_bound, epsilon):
    delta_step = 0.001
    deltas = numpy.arange(0, 1, delta_step)

    count_deltas={}

    for delta in deltas:
        count_deltas.update({delta:{"count":0, "callstacks":[]}})

    for rank_data in data:
        for callstack, values in rank_data.items():
            min_delta=0
            min_distance=float("inf")

            point = [values["times"], values["time_mean"]]
            my_delta = (point[0]*point[1])/total_time

            for delta in deltas:
                dist = (delta-my_delta)**2
                if dist < min_distance:
                    min_distance = dist
                    min_delta = delta

            count_deltas[min_delta]["count"] += 1
            count_deltas[min_delta]["callstacks"]\
                .append("{0}#{1}".format(rank_data[callstack]["rank"], callstack))

    #
    # Now, we want to concentrate deltas on peaks
    #
    concentrate_deltas(count_deltas, deltas)

    #
    # Modifying data after concentration
    #
    sum_deltas=0
    for delta, values in count_deltas.items():
        if values["count"] > 0: sum_deltas += delta
        for callstack in values["callstacks"]:
            rank=int(callstack.split("#")[0])
            key=callstack.split("#")[1]

            data[rank%len(data)][key]["delta"] = delta

    assert sum_deltas <= 1, "Delta's sum can not exceed 1 but is {0}."\
            .format(sum_deltas)

    result=[]
    for delta, value in count_deltas.items(): 
        if value["count"] > 0: result.append(delta)
    return result

def concentrate_deltas(count_deltas, deltas):

    ### Clustering ###
    points=[]
    for delta, value in count_deltas.items():
        points.append([value["count"]])
            
    #
    # 2. Perform clustering
    #
    db = DBSCAN(eps=0.1, min_samples=2).fit(normdata)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels=db.labels_

    clustered_cs={}
    for l in labels: 
        clustered_cs.update({l:[]})

    label_index=0
    for cs in cdist:
        for k,v in cs.items():
            clustered_cs[labels[label_index]].append({k:v})
            label_index+=1

    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    # TODO

    
    ### Detecting peaks ###
    
    import peakutils
    cb=[]
    for delta in deltas: 
        cb.append(count_deltas[delta]["count"])

    cb=numpy.array(cb)
    indexes = peakutils.indexes(cb, thres=0.02/max(cb), min_dist=10)

    deltas_to_concentrate = []
    for i in indexes:
        deltas_to_concentrate.append(deltas[i])

    #
    # Concentrating deltas in those peaks
    #
    sum_deltas_to_concentrate = 0
    for delta_tc in deltas_to_concentrate:
        sum_deltas_to_concentrate += count_deltas[delta_tc]["count"]

    deltas_to_concentrate = sorted(
            deltas_to_concentrate, 
            key=lambda x: count_deltas[x]["count"])

    for delta in deltas_to_concentrate:
        # IMPORTANT DECISSION
        _from = delta-float(count_deltas[delta]["count"])/sum_deltas_to_concentrate
        _to = delta+float(count_deltas[delta]["count"])/sum_deltas_to_concentrate

        aggregated_count=0
        aggregated_callstacks=[]
        for d in deltas:
            if d >= _from and d <= _to:
                aggregated_count += count_deltas[d]["count"]
                aggregated_callstacks.extend(count_deltas[d]["callstacks"])

                count_deltas[d]["count"] = 0
                count_deltas[d]["callstacks"]=[]

        count_deltas[delta]["count"] = aggregated_count
        count_deltas[delta]["callstacks"] = aggregated_callstacks

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
            min_distance = get_minimum_distance(delta, total_time, point)**2
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
    a=-1/T; b=X/T; c=T; d=-Y

    x=Symbol("x",real=True)
    solutions = solve(2*x**4 - 2*X*x**3 + 2*T*Y*x - 2*T**2, x)
    #solutions = solve(a*x**3 + b*x**2 + c*(1/x) + d, x)

    # Once we have de solutions we want to get the minimum distance
    min_distance = float("inf")
    for solution in solutions:
        #distance = math.sqrt((solution-X)**2 + ((T/solution)-Y)**2)
        distance = (solution-X)**2 + ((T/solution)-Y)**2

        if distance < min_distance:
            min_distance = distance
    
    return min_distance
