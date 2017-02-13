#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8


import sys,numpy, random
import constants
from utilities import merge_arrays
from spectrum import *

random.seed(constants.RANDOM_SEED)

def get_distances(times):
    dist=[]
    for i in range(1,len(times)):
        dist.append(times[i]-times[i-1])
    return dist

def getCsDistributions(filecs):
    nline=0
    callstacks={}
    with open(filecs) as filein:
        for line in filein:
            rank=line.split(constants._inter_field_separator)[0]
            time=line.split(constants._inter_field_separator)[1]
            lines=line.split(constants._inter_field_separator)[2]
            cs=line.split(constants._inter_field_separator)[3][:-1]

            # Because during the alignement some callstacks has been
            # ignored
            if len(cs)==0: 
                continue

            cs_lines_merged = merge_arrays(
                    cs.split(constants._intra_field_separator),
                    lines.split(constants._intra_field_separator))

            assert cs_lines_merged != None, \
                "Calls and lines merges can not be done."

            key=constants._intra_field_separator.join(cs_lines_merged)

            if not key in callstacks: 
                callstacks.update({
                    key:{
                        "occu":[nline],
                        "when":[int(time)], 
                        "rank":rank,}})
            else: 
                callstacks[key]["occu"].append(nline)
                callstacks[key]["when"].append(int(time))
            nline+=1

    cstack_res={}
    for callstack, data in callstacks.items():
        do=get_distances(data["occu"])
        tt=get_distances(data["when"])

        if not len(do) == 0:
            dmean=numpy.mean(do)
            dsdev=numpy.std(do)

            tmean=numpy.mean(tt)
            tsdev=numpy.std(tt)

            # Calcule the center in a timeline of the first time this
            # call is iterating (think about nested loops)
            
            sorted(data["when"])
            wmean=1    
            
            cstack_res.update({callstack:{
                #"dist_mean":dmean,
                #"dist_std" :dsdev,
                #"time_std" :tsdev,
                "when_mean":wmean,
                "time_mean":tmean,
                "when":data["when"],
                "rank":data["rank"],
                "times":len(data["occu"])}
                })

    return cstack_res
