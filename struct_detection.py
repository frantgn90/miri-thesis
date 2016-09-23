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

    #merge_cs(clustered_data[0])

    # Remove all temporal files
    for csf in cs_files: os.remove(csf)

    # Printing results
    '''
    lmat=numpy.matrix(loops_series)
    iterations=numpy.asarray(lmat.mean(0))[0]

    print("[Have been found {0} iterations]".format(len(iterations)))
    cnt=1
    for i in range(len(iterations)-1):
        print("  Iteration_{0} found @ [ {1} , {2} )".format(cnt,iterations[i],iterations[i+1]))
        cnt+=1
    print("  Iteration_{0} start @ {1}".format(cnt,iterations[-1]))
    '''
 
    print("[Results]")
    print("  -> {0} clusters detected".format(nclusters))
    print("  -> Really useful time (in loops): {0:.2f} %".format(mean_delta*100))
    print("[Done]")

    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
