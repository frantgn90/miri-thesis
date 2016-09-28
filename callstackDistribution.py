#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>

*****************************************************************************
*                        ANALYSIS PERFORMANCE TOOLS                         *
*                              [tool name]                                  *
*                         [description of the tool]                         *
*****************************************************************************
*     ___     This library is free software; you can redistribute it and/or *
*    /  __         modify it under the terms of the GNU LGPL as published   *
*   /  /  _____    by the Free Software Foundation; either version 2.1      *
*  /  /  /     \   of the License, or (at your option) any later version.   *
* (  (  ( B S C )                                                           *
*  \  \  \_____/   This library is distributed in hope that it will be      *
*   \  \__         useful but WITHOUT ANY WARRANTY; without even the        *
*    \___          implied warranty of MERCHANTABILITY or FITNESS FOR A     *
*                  PARTICULAR PURPOSE. See the GNU LGPL for more details.   *
*                                                                           *
* You should have received a copy of the GNU Lesser General Public License  *
* along with this library; if not, write to the Free Software Foundation,   *
* Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA          *
* The GNU LEsser General Public License is contained in the file COPYING.   *
*                                 ---------                                 *
*   Barcelona Supercomputing Center - Centro Nacional de Supercomputacion   *
*****************************************************************************
'''


import sys,numpy

import constants

_freq_tolerance=5 # TODO: Que sea un factor de, en vez de un natural

def merge_arrays(a, b):
    tlen=(len(a)+len(b))
    c=[None]*tlen

    for i in range(0, tlen, 2):
        if i/2 < len(a): c[i]=a[i/2]
        if i/2 < len(b): c[i+1]=b[i/2]

    return c

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

            key=constants._intra_field_separator.join(
                    merge_arrays(cs.split(constants._intra_field_separator),
                                 lines.split(constants._intra_field_separator)))

            #key=cs

            if not key in callstacks: 
                callstacks.update({key:{"occu":[nline],"when":[int(time)], "rank":rank,}})
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
        
            cstack_res.update({callstack:{
                "dist_mean":dmean,
                "dist_std" :dsdev,
                "time_mean":tmean,
                "time_std" :tsdev,
                "when":data["when"],
                "rank":data["rank"],
                "times":len(data["occu"])}
                })

    return cstack_res

def getLoops(cdist):
    #IDEA: Apply clustering with times and dist_mean as features

    #mock-up: In the case of lulesh, we have only one loop with
    #then iterations. It has been detected that 21 mpi calls forms part
    #of this loop and we want to print the init of every iteration of the loop

    min_first_time=sys.maxint
    first_call_iter=None
    for cs,val in cdist.items():
        if val["when"][0] < min_first_time:
            min_frist_time=val["when"][0]
            first_call_iter=val

    return first_call_iter["when"]
