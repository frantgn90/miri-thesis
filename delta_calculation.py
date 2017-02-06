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

_bottom_bound=0.10
_upper_bound=1
_init_delta=0.5

# Delta is bounded by (_bottom_bound, 1)


def getCost(lmbda, T, P, delta):
    return lmbda-((T*delta)/P)

'''
TODO: Implement this function with the descent gradient technique in order to
increase the performance of finding the optimal delta
'''
def getDelta(cdist, total_time):

    # First of all we have to discard all clusters  that are below
    # the bottom boundary
    filtered_cdist={ k:v for k,v in cdist.items() if getCost(v["times"],total_time,v["time_mean"],_bottom_bound) > 0 }

    cost=sys.maxint
    delta=_init_delta
    optimal=delta

    for delta in numpy.arange(_bottom_bound, _upper_bound, 0.01):
        mean_cost=0
        for cs,data in filtered_cdist.items():
            pcost=abs(getCost(data["times"], total_time, data["time_mean"], delta))
            mean_cost+=pcost

        mean_cost/=len(filtered_cdist)

        if mean_cost < cost:
            optimal=delta
            cost=mean_cost

    return optimal, filtered_cdist

