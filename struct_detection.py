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

    #
    # 1. Parsing trace
    #
    logging.info("Parsing trace")

    if not tmp_files_dir is None:
        import glob
        cs_files = glob.glob("{0}/*.aligned".format(tmp_files_dir))

        assert len(cs_files) > 0
        logging.info("Using already generated data")
    else:
        try:
            cs_files=get_callstacks(
                    trace=trace, 
                    level=level, 
                    image_filter=image_filter)
        except OSError:
            logging.error("Oops! It seems that tracefile does not exists!")
            return 1
        
    app_time = get_app_time(trace)
    nranks=len(cs_files)

    logging.debug("{0} ranks detected.".format(nranks))
    logging.debug("{0} ns total trace time.".format(app_time))
    
    #
    # 2. Getting callstack metrics
    #
    logging.info("Merging repeated callstacks and deriving information")
    
    depured_data = []
    for csf in cs_files:
        depured_csf = getCsDistributions(csf)
        if len(depured_csf) > 0:
            depured_csf = filter_under_delta(
                    depured_csf, 
                    app_time, 
                    arguments.bottom_bound[0])

            depured_data.append(depured_csf)

    depured_data = sorted(depured_data, key=lambda x: x[x.keys()[0]]["rank"])
    #depured_data = [depured_data[1]]


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
        deltas = calcule_deltas_cplex(
                depured_data,
                app_time,
                arguments.bottom_bound[0],
                arguments.delta_accuracy[0],
                arguments.cplex_input[0])

    logging.info("Used deltas: {0}".format(deltas))

    #
    # 3. Clustering
    #
    logging.info("Performing clustering")
    nclusters, cluster_objects=clustering(
            #filtered_data, 
            depured_data,

            nranks, 
            arguments.show_clustering, 
            app_time, 
            deltas,
            arguments.bottom_bound[0])
    logging.info("{0} clusters detected".format(nclusters))

    #
    # 4. Merging clusters
    #
    logging.info("Merging clusters")

    top_level_clusters = merge_clusters(
                            cluster_set=cluster_objects,
                            ranks=nranks)

    # 4.1. Getting random iterations for every cluster
    if arguments.nrandits > 0:
        logging.info("Getting random iterations from clusters")
        iterations = get_random_iters(
                clusters=cluster_objects,
                n_random_iterations=arguments.n_random_iterations)
    else:
        iterations = []

    #
    # 5. Generating pseudocode
    #
    logging.info("Generating pseudocode for {0} top level clusters"
            .format(len(top_level_clusters)))

    pseudocode=""
    for cluster in top_level_clusters:
        pseudocode += cluster.str()

    pretty_print(pseudocode, trace)

    #
    # 6. Print some statistics
    #
    if ri > 0:
        print_iterations(iterations)

    final_stats =  ">> {0} clusters detected\n".format(nclusters)
    final_stats+=  ">> Grouped in {0} super-loops\n".format(len(deltas))

    for i, delta in zip(range(len(deltas)),deltas):
        final_stats+=(" > Top level loop {0} = {1}%\n".format(i, delta*100)) 
    final_stats+=(">> Time in pseudocode: {0}%\n".format(sum(deltas)*100))

    pretty_print(final_stats, "Final stats")

    #
    # 7. Remove all temporal files
    #
    #for csf in cs_files: 
    #    os.remove(csf)

    logging.info("All done")
    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
