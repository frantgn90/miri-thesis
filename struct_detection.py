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
from pseudoCodeGenerator import *

import constants

def pretty_print(pseudocode):
    print("+"+"-"*78+"+")
    print("|"+" "*78+"|")
    pseudocode=pseudocode.split("\n")
    for line in pseudocode:
        pline = "|  " + line + " "*(76-len(line))+"|"
        print(pline)

    print("+"+"-"*78+"+")


def Usage(cmd):
    print("Usage(): {0} [-l call_level] [-f img1[,img2,...]] <trace>\n"
        .format(cmd))
    exit(1)


def main(argc, argv):
    if argc < 2:
        Usage(argv[1])
        
    #######################################
    ####### PREPARE AND SHOW PARAMS #######
    #######################################
    level="0"; trace = argv[-1]; image_filter=["ALL"]
    for i in range(1, len(argv)-1):
        if argv[i] == "-f": image_filter=argv[i+1].split(",")
        elif argv[i] == "-l": level=argv[i+1]

    clevels = "All"
    if level != "0": clevels=str(level)

    if constants._verbose: print("{0} : Calls level={1}; Image filter={2}; Trace={3}\n\n"
        .format(argv[0], clevels, str(image_filter), trace.split("/")[-1]))


    #######################################
    ####### GETTING DATA FROM TRACE #######
    #######################################
    cs_files,app_time=get_callstacks(trace, level, image_filter)
    nranks=len(cs_files)


    ########################################
    ###### GETTING CALLSTACKS METRICS ######
    ########################################
    if constants._verbose: print("[Merging data]")
    mean_delta=0; filtered_data=[]; nonfiltered_data=[]
    for csf in cs_files:
        cdist=getCsDistributions(csf)
        new_delta, new_fdata=getDelta(cdist,app_time)
        mean_delta+=new_delta
        filtered_data.append(new_fdata)
        nonfiltered_data.append(cdist)

    mean_delta/=len(cs_files)


    ########################
    ###### CLUSTERING ######
    ########################
    if constants._verbose: print("[Performing clustering]")
    nclusters, clustered_data=clustering(filtered_data, False)


    #########################################################
    ###### GENERATING PSEUDO-CODE AND PRINTING RESULTS ######
    #########################################################
    print("[Generating pseudocode]")
    print("")

    pseudocode=generate_pseudocode(clustered_data, nranks)

    pretty_print(pseudocode)

    print("[Results]")
    print("  -> {0} clusters detected".format(nclusters))
    print("  -> Really useful time (in loops): {0:.2f} %".format(mean_delta*100))

    # Remove all temporal files
    for csf in cs_files: os.remove(csf)

    print("[Done]")
    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
