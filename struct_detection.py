#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, os
import numpy

from trace_parsing import *
from callstack_distribution import *
from delta_calculation import *
from clustering import *
from pseudocode_generator import *
from utilities import *


import constants

def Usage(cmd):
    print("Usage(): {0} [-l call_level] [-f img1[,img2,...]] [-ri N] <trace>\n"
        .format(cmd))
    exit(1)


def main(argc, argv):
    if argc < 2:
        Usage(argv[0])
        
    # Prepare and show params
    level="0"; trace = argv[-1]; image_filter=["ALL"]; ri=0
    for i in range(1, len(argv)-1):
        if argv[i] == "-f": image_filter=argv[i+1].split(",")
        elif argv[i] == "-l": level=argv[i+1]
        elif argv[i] == "-ri": ri=int(argv[i+1])

    clevels = "All"
    if level != "0": clevels=str(level)

    if constants._verbose: print("{0} : Calls level={1}; Image filter={2}; Trace={3}\n\n"
        .format(argv[0], clevels, str(image_filter), trace.split("/")[-1]))


    # 1. Parsing trace
    cs_files,app_time=get_callstacks(trace, level, image_filter)
    nranks=len(cs_files)


    # 2. Getting callstack metrics
    if constants._verbose: print("[Merging data]")
    mean_delta=0; filtered_data=[]; nonfiltered_data=[]
    for csf in cs_files:
        cdist=getCsDistributions(csf)
        new_delta, new_fdata=getDelta(cdist,app_time)
        mean_delta+=new_delta
        filtered_data.append(new_fdata)
        nonfiltered_data.append(cdist)

    mean_delta/=len(cs_files)

    # 3. Clustering
    if constants._verbose: print("[Performing clustering]")
    nclusters, clustered_data=clustering(filtered_data, False)

    # 4. Generate pseudocode
    if constants._verbose: print("[Generating pseudocode]"); print("")

    pseudocode, iterations=generate_pseudocode(clustered_data, nranks, ri)
    pretty_print(pseudocode, trace)

    # 5. Print some statistics
    if ri > 0:
        print_iterations(iterations)

    final_stats="> {0} clusters detected\n".format(nclusters)
    final_stats+="> Time in pseudocode: {0:.2f} % \n"\
            .format(mean_delta*100)
    final_stats+="> Discarded calls time: {0:.2f} % \n"\
            .format(100-(mean_delta*100))
    pretty_print(final_stats, "Final stats")

    # 6. Remove all temporal files
    for csf in cs_files: os.remove(csf)

    print
    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
