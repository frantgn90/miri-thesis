#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Delta is the portion of the execution that has been executed by mean of loops
Could be said that is the portion of the execution of really work. 1-Delta can be
initializations and last treatments of data.
'''

import sys
import numpy

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

def set_deltas(depured_data, total_time, bottom_bound, epsilon):

    deltas=[]
    delta_step=epsilon
   
    total_callstacks = 0
    for data in depured_data:
        total_callstacks+=len(data)

    total_covered = 0
    while not total_covered == total_callstacks:
        max_covered = 0
        for current_delta in numpy.arange(1, bottom_bound, -delta_step):
            calls_covered=0
            for data in depured_data:
                for d in deltas: # Filtering the current covered calls
                    data = {k: v for k, v in data.items() if v["delta"] == None}

                filtered = filter_by_delta_range(
                        data, 
                        total_time, 
                        current_delta-epsilon,
                        current_delta+epsilon)
                calls_covered+=len(filtered)

            if calls_covered > max_covered:
                max_covered = calls_covered
                optimum_delta = current_delta

        if max_covered > 0:
            deltas.append(optimum_delta)
            total_covered+=max_covered

            for data in depured_data:
                to_set_delta = filter_by_delta_range(
                        data,
                        total_time,
                        optimum_delta-epsilon,
                        optimum_delta+epsilon)

                for k,v in to_set_delta.items():
                    data[k]["delta"] = optimum_delta

                    
    
    return deltas
