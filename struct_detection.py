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
            help="The clusters that explains a portion below this boundary will be ignored",
            metavar="BOUND",
            dest="bottom_bound")

    parser.add_argument("--log",
            action="store",
            nargs=1,
            type=str,
            required=False,
            default=["WARNING"],
            help="Log level",
            metavar="LOG",
            dest="log_level")


    argcomplete.autocomplete(parser)
    arguments = parser.parse_args(args=argv[1:])

    trace = arguments.prv_trace[0]
    level = arguments.call_level[0]
    image_filter = arguments.image_filter
    ri = arguments.nrandits
    tmp_files_dir = arguments.tmp_files[0]

    numeric_level = getattr(logging, arguments.log_level[0].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

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

    mean_delta=0; 
    filtered_data=[];
    for csf in cs_files:
        cdist=getCsDistributions(filecs=csf)
        cdist_filtered = filterIrrelevant(
                cdist, 
                app_time, 
                arguments.bottom_bound[0])
        if len(cdist_filtered) > 0:
            new_delta=getDelta(
                    cdist_filtered, 
                    app_time, 
                    arguments.bottom_bound[0])
        else:
            new_delta = 0
        
        logging.debug("[{0}]:Bound={1} Delta = {2} Discarded = {3}"\
                .format(
                    csf, 
                    arguments.bottom_bound[0],
                    new_delta, len(cdist)-len(cdist_filtered)))

        mean_delta+=new_delta
        filtered_data.append(cdist_filtered)
    mean_delta/=len(filtered_data)

    if mean_delta == 0:
        logging.info("{0} boundary is filtering all data"\
                .format(arguments.bottom_bound[0]))
        return 0
    
    #
    # 3. Clustering
    #
    logging.info("Performing clustering")
    nclusters, cluster_objects=clustering(
            filtered_data, 
            nranks, 
            arguments.show_clustering)
    logging.info("{0} clusters detected".format(nclusters))

    #
    # 4. Merging clusters
    #
    logging.info("Merging clusters")

    #cnt=0
    #for clt in clustere_objects:
    #    logging.debug("Pseudo-code for cluster {0}".format(cnt))
    #    logging.debug(clt.str())
    #    cnt+=1

    merged_cluster = merge_clusters(
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
    logging.info("Generating pseudocode")
    pseudocode = merged_cluster.str()

    pretty_print(pseudocode, trace)

    #
    # 6. Print some statistics
    #
    if ri > 0:
        print_iterations(iterations)

    final_stats="> {0} clusters detected\n".format(nclusters)
    final_stats+="> Time in pseudocode: {0:.2f} % \n".format(mean_delta*100)
    final_stats+="> Discarded calls time: {0:.2f} % \n".format(100-(mean_delta*100))

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
