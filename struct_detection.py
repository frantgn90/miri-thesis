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

import sys, os
import numpy

from traceParsing import *
from callstackDistribution import *
from calculateDelta import *
from clustering import *

import constants

# This function performs all the matrix transformation (gaps add) needed
# in order to guarantee the constraint of iterations non-overlaping.
# i.e. the last element of col n must be less or equal that the first
# element of n+1 col
def boundaries_sort(tmat):
    matrix=tmat.tolist()
    ncols=len(matrix[0])
    nrows=len(matrix)

    for row in range(1, nrows):
        for col in range(ncols):
            rindex=0
            head=matrix[rindex][col+1]
            while head==-1:
                rindex+=1
                head=matrix[rindex][col+1]

            print("Comparison {0} > {1}".format(matrix[row][col], head))
            if matrix[row][col] > head:
                # Then move to right
                for above_rows in range(0, row):
                    matrix[above_rows]=matrix[above_rows]+[-1]

                for below_rows in range(row, nrows):
                    matrix[below_rows]=[-1]+matrix[below_rows]

    return numpy.array(matrix)

def calculate_it_boundaries(cluster):

    # TODO: Cation with the empty holes... for the moment
    # -1 is put to the right hand side.

    tomat=[]
    index=0
    max_size=0
    keys_cs=[]

    for cs in cluster:
        k=cs.keys()[0]
        
        if cs[k]["rank"] != "0": continue

        if len(cs[k]["when"]) > max_size:
            max_size=len(cs[k]["when"]) 
            for i in range(index-1, -1, -1):
                holes=max_size-len(tomat[i])
                tomat[i].extend([-1]*holes)
        elif len(cs[k]["when"]) < max_size:
            holes=max_size-len(cs[k]["when"])
            cs[k]["when"].extend([-1]*holes)

        tomat.append(cs[k]["when"])
        keys_cs.append(k)
        index+=1

    ki=0
    for row in tomat:
        row.append(ki)
        ki+=1

    tmat=numpy.matrix(tomat)
    tmat=tmat.view("i8,"*(max_size-1)+"i8,i8")
    tmat.sort(order=["f0"], axis=0)
    tmat=tmat.view(np.int)

    ordered_calls=tmat[:,max_size].transpose()

    # Get the calls ordered by times
    keys_ordered=[]
    for row in range(len(keys_cs)):
        ki=tmat.item((row,-1))
        keys_ordered.append(keys_cs[ki])

    
    # TODO: Necesito la matriz sin la info sobre callstacks
    boundaries_sort(tmat)

    # Get the iterations times
    iterations=[]
    for it in range(max_size+1):
        ite=tmat[:,it].transpose().tolist()[0]
        
        index_from=0
        from_time=ite[index_from]

        while from_time == -1:
            index_from+=1
            from_time=ite[index_from]

        index_to=-1
        to_time=ite[index_to]

        while to_time == -1:
            index_to-=1
            to_time=ite[index_to]

        iterations.append((from_time,to_time))

    return iterations, keys_ordered
    #return tmat.tolist()[0][:-1], keys_ordered 

def main(argc, argv):
    if argc < 2:
        print("Usage(): {0} [-l call_level] [-f img1[,img2,...]] <trace>\n"
                .format(argv[0]))
        return -1

    level="0"; trace = argv[-1]; image_filter=["ALL"]
    for i in range(1, len(argv)-1):
        if argv[i] == "-f": image_filter=argv[i+1].split(",")
        elif argv[i] == "-l": level=argv[i+1]

    clevels = "All"
    if level != "0":
        clevels=str(level)

    if constants._verbose:
        print("{0} : Calls level={1}; Image filter={2}; Trace={3}\n\n"
                .format(argv[0], clevels, str(image_filter), trace.split("/")[-1]))

    cs_files,app_time=get_callstacks(trace, level, image_filter)

    if constants._verbose: print("[Merging data]")

    mean_delta=0; filtered_data=[]; nonfiltered_data=[]
    for csf in cs_files:
        cdist=getCsDistributions(csf)
        new_delta, new_fdata=getDelta(cdist,app_time)
        mean_delta+=new_delta
        filtered_data.append(new_fdata)
        nonfiltered_data.append(cdist)

        '''
        print("callstack\ttimes\ttime_mean\ttime_std\tdist_mean\tdist_std")
        for c,d in cdist.items():
            print("{0}\t{1}\t{2:.2f}\t{3:.2f}\t{4:.2f}\t{5:.2f}"
                .format(c,d["times"], d["time_mean"], d["time_std"], d["dist_mean"], d["dist_std"], d["when"]))
        '''

    mean_delta/=len(cs_files)
    nclusters, clustered_data=clustering(filtered_data, False)

    # Printing results
    ordered_cluster={}
    for cluster in clustered_data.keys():
        it_cluster,cs_ordered=calculate_it_boundaries(clustered_data[cluster])
        
        print("[\033[1mCluster {0}\033[0m have been found {1} iterations]".format(cluster, len(it_cluster)))
        cnt=1
        for i in range(len(it_cluster)-1):
            print("-  Iteration_{0} found @ [ {1} , {2} )".format(cnt,it_cluster[i][0],it_cluster[i][1]))
            cnt+=1

        #print("-  Iteration_TOT found @ [ {0} , {1} ]".format(it_cluster[0][0], it_cluster[0][0]+app_time*mean_delta))
        print("[Every iteration has this calls]")
        for cs in cs_ordered:
            print("-  {0}".format(cs))
        
    print("[Results]")
    print("  -> {0} clusters detected".format(nclusters))
    print("  -> Really useful time (in loops): {0:.2f} %".format(mean_delta*100))
    print("[Done]")

    # Remove all temporal files
    for csf in cs_files: os.remove(csf)

    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
