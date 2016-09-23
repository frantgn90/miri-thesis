#!/usr/bin/env python

'''
./callstack_from_trace.py 

This scripts is the responsible to 
'''

import sys, os
import numpy

from traceParsing import *
from callstackDistribution import *
from calculateDelta import *
from clustering import *

import constants

def calculate_it_boundaries(cluster):
    tomat=[]
    index=0
    max_size=0
    for cs in cluster:
        k=cs.keys()[0]
        
        if cs[k]["rank"] != "0": continue

        if len(cs[k]["when"]) > max_size:
            max_size=len(cs[k]["when"]) 
            for i in range(index-1, 0, -1):
                holes=max_size-len(tomat[i])
                tomat[i].extend([-1]*holes)
        elif len(cs[k]["when"]) < max_size:
            holes=max_size-len(cs[k]["when"])
            cs[k]["when"].extend([-1]*holes)

        tomat.append(cs[k]["when"])
        index+=1

    tmat=numpy.matrix(tomat)
    tmat=numpy.sort(tmat.view("i8,"*(max_size-1)+"i8"), order=["f0"], axis=0)

    print tmat.tolist()[0][0]
    return tmat.tolist()[0][0]

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

    mean_delta=0; filtered_data=[]
    for csf in cs_files:
        cdist=getCsDistributions(csf)
        new_delta, new_fdata=getDelta(cdist,app_time)
        mean_delta+=new_delta
        filtered_data.append(new_fdata)

        '''
        print("callstack\ttimes\ttime_mean\ttime_std\tdist_mean\tdist_std")
        for c,d in cdist.items():
            print("{0}\t{1}\t{2:.2f}\t{3:.2f}\t{4:.2f}\t{5:.2f}"
                .format(c,d["times"], d["time_mean"], d["time_std"], d["dist_mean"], d["dist_std"], d["when"]))
        '''


    mean_delta/=len(cs_files)
    nclusters, clustered_data=clustering(filtered_data)
    it_cluster=calculate_it_boundaries(clustered_data[1])

    # Printing results
    print("[Have been found {0} iterations]".format(len(it_cluster)))
    cnt=1
    for i in range(len(it_cluster)-1):
        print("  Iteration_{0} found @ [ {1} , {2} )".format(cnt,it_cluster[i],it_cluster[i+1]))
        cnt+=1
    print("  Iteration_{0} start @ {1}".format(cnt,it_cluster[-1]))
    print("  Iteration_TOT found @ [ {0} , {1} ]".format(it_cluster[0], it_cluster[0]+app_time*mean_delta))
    
 
    print("[Results]")
    print("  -> {0} clusters detected".format(nclusters))
    print("  -> Really useful time (in loops): {0:.2f} %".format(mean_delta*100))
    print("[Done]")

    # Remove all temporal files
    for csf in cs_files: os.remove(csf)

    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
