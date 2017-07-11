#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, os
import numpy

import logging
import argparse, argcomplete

from trace_parsing import *
from callstack_distribution import *
from delta_calculation import *
from clustering import *
from pseudocode_generator import *
from utilities import *
from flowgraph import flowgraph
from pseudocode import pseudocode
from cluster import merge_clusters

import constants

def Usage(cmd):
    print("Usage(): {0} [-l call_level] [-f img1[,img2,...]] [-ri N] <trace>\n"
        .format(cmd))
    exit(1)


def main(argc, argv):

    parser = argparse.ArgumentParser(
        description="This script analyze a Paraver trace in order to extract the needed"\
                " information for infer the internal structure of the traced application."\
                " This analysis can be used for improve the understanding of the"\
                " analyzed application.")

    parser.add_argument("--trace",
            action="store",
            nargs=1,
            type=str,
            required=True,
            help="The Paraver trace to be analyzed.",
            metavar="PRVTRACE",
            dest="prv_trace")
    
    parser.add_argument("--call-level",
            action="store",
            nargs=1,
            type=str,
            required=False,
            default="0",
            help="Until which callstack level the analyzer will look at.",
            metavar="CALLLEVEL",
            dest="call_level")

    parser.add_argument("--image-filter",
            action="store",
            nargs="?",
            type=str,
            required=False,
            default=["ALL"],
            help="The callstack for these images will be taken into account by the analyzer.",
            metavar="IMAGES",
            dest="image_filter")

    parser.add_argument("--random-iterations",
            action="store",
            nargs=1,
            type=int,
            required=False,
            default=0,
            help="Number of random iterations to show for every detected loop.",
            metavar="NRANDIT",
            dest="nrandits")

    parser.add_argument("--show-clustering",
            action="store_true",
            help="Whether you want the clustering shows up.",
            dest="show_clustering")

    parser.add_argument("--temp-files-dir",
            action="store",
            nargs=1,
            type=str,
            required=False,
            default=[None],
            help="Whether you want to use already generated temporal data.",
            metavar="TMPFILESDIR",
            dest="tmp_files")

    parser.add_argument("--bottom-bound",
            action="store",
            nargs=1,
            type=float,
            required=False,
            default=[0.01],
            help="The clusters that explains a portion below this boundary will"\
                    " be ignored",
            metavar="BOUND",
            dest="bottom_bound")

    parser.add_argument("--epsilon",
            action="store",
            nargs=1,
            type=float,
            required=False,
            default=[0.01],
            help="When delta analysis is performed, the epsilon is the relative"\
                    " tolerated area.")

    parser.add_argument("--log",
            action="store",
            nargs=1,
            type=str,
            required=False,
            default=["WARNING"],
            help="Log level",
            metavar="LOG",
            dest="log_level")

    parser.add_argument("--cplex",
            action="store_true",
            help="Whether you want that the delta calculation will be done by"\
                    " CPLEX optimization engine or by a heuristics.",
            dest="use_cplex")

    parser.add_argument("--cplex-input",
            action="store",
            nargs=1,
            type=str,
            required=False,
            default=[None],
            help="Whether you want to use already generated input for CPLEX, you "\
                    "must specify here the path to it.",
            metavar="CPLEXINPUT",
            dest="cplex_input")

    parser.add_argument("--delta-accuracy",
            action="store",
            nargs=1,
            type=float,
            required=False,
            default=[0.1],
            help="Inverse of number of deltas provided to cplex.")


    argcomplete.autocomplete(parser)
    arguments = parser.parse_args(args=argv[1:])

    trace = arguments.prv_trace[0]
    level = arguments.call_level[0]
    image_filter = arguments.image_filter
    ri = arguments.nrandits
    tmp_files_dir = arguments.tmp_files[0]
    numeric_level = getattr(logging, arguments.log_level[0].upper(), None)

    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: {0}".format(loglevel))
    logging.basicConfig(level=numeric_level)

    ''''''''''''''''''''''''''
    ''' Workflow starting  '''
    ''''''''''''''''''''''''''

    ''' 1. Parsing trace '''
    logging.info("Parsing trace...")
    callstacks_pool=get_callstacks(trace=trace, level=level, image_filter=image_filter)
    app_time = get_app_time(trace)
    logging.debug("{0} ns total trace time.".format(app_time))
    
    
    ''' 2. Getting callstack metrics '''
    logging.info("Reducing information")
    for callstack in callstacks_pool:
        callstack.calc_reduce_info()


    ''' 3. Filtering below delta '''
    logging.info("Filtering callstacks below delta...")
    fcallstacks_pool=filter(
            lambda x: x.is_above_delta(app_time, arguments.bottom_bound[0]),
            callstacks_pool)
    logging.info("Reduced from {0} to {1}".format(
        len(callstacks_pool), len(fcallstacks_pool)))


    ''' 4. Callstacks to delta mapping '''
    logging.info("Detecting super-loops")
    if not arguments.use_cplex:
        logging.info("Calculating delta by mean of heuristics.")
        deltas = calcule_deltas_heuristic(
                depured_data, 
                app_time,
                arguments.bottom_bound[0],
                arguments.epsilon[0])

        deltas.sort()
        logging.info("Deltas: {0}".format(deltas))
    else:
        logging.info("Calculating delta by mean of CPLEX.")
        deltas = calcule_deltas_cplex(fcallstacks_pool,app_time,
                arguments.bottom_bound[0],
                arguments.delta_accuracy[0],
                arguments.cplex_input[0])

    logging.info("{0} super-loops detected".format(len(deltas)))


    ''' 5. Clustering '''
    logging.info("Performing clustering")
    clusters_pool=clustering(fcallstacks_pool, arguments.show_clustering, 
            app_time, deltas, arguments.bottom_bound[0])
    for cluster in clusters_pool:
        cluster.run_loops_generation()

    logging.info("{0} clusters detected".format(len(clusters_pool)))

    ''' 6. Merging clusters '''
    logging.info("Merging clusters...")
    top_level_clusters = merge_clusters(clusters_pool)
    logging.info("Done")

#    for cluster in top_level_clusters:
#        print cluster
#    exit(0)

    ''' 7. Genearting flowgraph '''
#    logging.info("Generating flowgraph...")
#    fg = flowgraph(top_level_clusters[0]) # TOCHANGE -> top_level_clusters 
#    logging.info("Done")
#
#    fg.show()


    ''' 7. Reducing callstacks '''
    logging.info("Compacting callstacks...")
    for cluster_obj in top_level_clusters:
        for loop_obj in cluster_obj.loops:
            loop_obj.compact_callstacks()
            loop_obj.detect_condition_bodies()
            print loop_obj
    logging.info("Done")


    ''' 8. Generating pseudo-code '''
    logging.info("Generating pseudocode...")
    pc = pseudocode(top_level_clusters)
    logging.info("Done...")

    pc.show_console()

    ''' 8. Print some statistics '''
    final_stats =  "{0} clusters detected\n".format(len(clusters_pool))
    final_stats+=  "Grouped in {0} super-loops\n".format(len(deltas))
    for i, delta in zip(range(len(deltas)),deltas):
        final_stats+=(" > Top level loop {0} = {1}%\n".format(i, delta*100)) 
    final_stats+=("Time in pseudocode: {0}%\n".format(sum(deltas)*100))

    print pretty_print(final_stats, "Final stats")

    logging.info("All done")
    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
