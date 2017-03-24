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

from sympy.solvers import solve,nsolve
from sympy import Symbol

import logging
import constants

from cplex_interface import CplexInterface
from utilities import ProgressBar
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

def calcule_deltas_cplex(
        depured_data, total_time, bottom_bound, delta_accuracy, cplex_input):
    #
    # Preparing data for CPLEX
    #

    npoints = 0
    for cs in depured_data:
        for k,v in cs.items():
            npoints+=1

    if cplex_input == None:
        logging.info("Preparing data for CPLEX")
        nDeltas = 1/delta_accuracy
        deltas=[]
        for i in numpy.arange(delta_accuracy, 1, delta_accuracy):
            deltas.append(i)
        deltas.append(1)

        pbar = ProgressBar("Generating CPLEX input", npoints*len(deltas))

        points=[]
        for cs in depured_data:
            for k,v in cs.items():
                points.append([v[constants._x_axis],v[constants._y_axis]])

        big_m = 0
        distance_dp = []

        for delta in deltas:
            distance_delta=[]
            for point in points:
                min_distance = get_minimum_distance(delta, total_time, point)
                min_distance_2 = get_minimum_distance_2(delta, total_time, point)

                print "{0} ~ {1}".format(min_distance, min_distance_2)
                distance_delta.append(min_distance)

                if min_distance > big_m:
                    big_m = min_distance

                logging.debug("Distances from point ({0},{1}) to delta {2} = {3}"
                        .format(point[0], point[1], delta, min_distance))
                pbar.progress_by(1)
                pbar.show()

            distance_dp.append(distance_delta)

        arguments = {
                constants.OPL_ARG_BIGM:    big_m,
                constants.OPL_ARG_NDELTAS: len(deltas),
                constants.OPL_ARG_NPOINTS: len(points),
                constants.OPL_ARG_DELTAS:  deltas,
                constants.OPL_ARG_POINTS:  points,
                constants.OPL_ARG_DISTDP:  distance_dp
        }

        cplex_int = CplexInterface()
        infile = cplex_int.set_args(arguments)

        logging.info("CPLEX infile generated: {0}".format(infile))
    else:
        logging.info("Using CPLEX input: {0}".format(cplex_input))
        cplex_int = CplexInterface()
        cplex_int.set_infile(cplex_input)

    #
    # Launching CPLEX
    #
    logging.info("Launching CPLEX for delta clasification...")

    logging.info("Using CPLEX outfile: {0}".format(cplex_int.get_outfile()))
    logging.info("Using CPLEX errfile: {0}".format(cplex_int.get_errfile()))

    cplex_int.run()  

    #
    # Update points delta
    #
    logging.info("Updating points delta clasification...")
    point_cnt = 0
    pbar = ProgressBar("Updating points", npoints)
    pbar.show()
    for cs in depured_data:
        for k,v in cs.items():
            v["delta"] = cplex_int.get_delta_point_map(point_cnt)
            point_cnt += 1
            pbar.progress_by(1)
            pbar.show()
            
    return cplex_int.get_used_deltas()

# Inspired on (last comment): http://math.stackexchange.com/questions/967268/
# finding-the-closest-distance-between-a-point-a-curve
def get_minimum_distance(delta,total_time, point):
    T=delta*total_time
    X=point[0]
    Y=point[1]
    a=2; b=-2*X; c=2*T*Y; d=-2*T**2

    x=Symbol("x",real=True)
    solutions = solve(a*x**4 + b*x**3 + c*x + d, x)

    # Once we have de solutions we want to get the minimum distance
    min_distance = float("inf")
    for solution in solutions:
        distance = math.sqrt((solution-X)**2 + ((T/solution)-Y)**2)

        if distance < min_distance:
            min_distance = distance
    
    return min_distance

def get_minimum_distance_2(delta, total_time, point):
    result = _get_minimum_distance_2(delta, total_time, point, 0, 0)
    return result

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

    h=(b*c)/a
    h = (-h if is_below else h)
    
    print "Below={0} : {1}".format(is_below, h)

    print "A={0}".format(point)
    print "B={0}".format(B)
    print "C={0}".format(C)

    if iteration < constants.MAX_ITERATIONS:
        #m=(b**2)/a
        #n=(c**2)/a

        m = math.sqrt(b**2-h**2)
        n = math.sqrt(c**2-h**2)

        print "n={0}; m={1}".format(n,m)

        if not is_below:
            coeff=float(m)/a
            new_point = [C[0]+b*coeff, C[1]+c*coeff]
        else:
            coeff=float(n)/a
            new_point = [X+b*coeff, Y+c*coeff]

        print "E={0}".format(new_point)

        print "--------------"
        return _get_minimum_distance_2(
                delta, 
                total_time, 
                new_point, 
                h+accumulated, 
                iteration+1)
    else:
        print "______________"
        return abs(h+accumulated)

