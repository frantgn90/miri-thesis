#! /usr/bin/env python2
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
from utilities import *
from flowgraph import flowgraph
from pseudocode import pseudocode
from cluster import merge_clusters
from sdshell import sdshell
import constants

def main(argc, argv):
    parser = argparse.ArgumentParser(
            description="This script analyze a Paraver trace in order to extract"\
                    " the needed information for infer the internal structure of"\
                    " the traced application. This analysis can be used for "\
                    " improve the understanding of the analyzed application.")

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
            help="The callstack for these images will be taken into account"\
                    " by the analyzer.",
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

    parser.add_argument("--only-mpi",
            action="store_true",
            help="Whether you want to see just MPI calls or the "\
                    "whole callstack",
            dest="only_mpi")

    #parser.add_argument("--output",
    #        action="store",
    #        nargs=1,
    #        type=str,
    #        required=False,
    #        default=[None],
    #        help="Whether you want the output into a file, indicate the file"\
    #                " whit this flag",
    #        metavar="OUTFILE",
    #        dest="output_filename")

    parser.add_argument("--in-mpi-metric",
            action="store",
            nargs='+',
            type=str,
            required=False,
            default=[],
            dest="in_mpi_events",
            help="In MPI Paraver event type(s) to gather information.")

    parser.add_argument("--html-gui",
            action="store_true",
            dest="html_output",
            help="Whether you want to display the output in an enriched"\
                    " html format")

    parser.add_argument("--in-program-order",
            action="store_true",
            help="Whether you want pseudocode callstacks in program order"\
                    " or in dynamic order",
            dest="in_program_order")

    parser.add_argument("--burst-info",
            action="store_true",
            help="Whether you want burst info be showed or not",
            dest="show_burst_info")


    argcomplete.autocomplete(parser)
    arguments = parser.parse_args(args=argv[1:])

    trace = arguments.prv_trace[0]
    level = arguments.call_level[0]
    image_filter = arguments.image_filter
    ri = arguments.nrandits
    tmp_files_dir = arguments.tmp_files[0]
    numeric_level = getattr(logging, arguments.log_level[0].upper(), None)

    in_mpi_events = arguments.in_mpi_events
    in_mpi_events.append("42000050") # instructions
    in_mpi_events.append("42000059") # events
    in_mpi_events.append("50100001") # send size in global op
    in_mpi_events.append("50100002") # recv size in global op
    in_mpi_events.append("50100004") # communicator in global op

    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: {0}".format(loglevel))

    constants.log_level = numeric_level

    # https://docs.python.org/2/library/logging.html#logrecord-attributes
    # FORMAT="[%(levelname)s] %(asctime)s - %(message)s"
    FORMAT="[%(levelname)s] (%(filename)s:%(lineno)s) %(message)s"
    logging.basicConfig(level=numeric_level, format=FORMAT)

    ''''''''''''''''''''''''''
    ''' Workflow starting  '''
    ''''''''''''''''''''''''''

    ''' 1. Parsing trace '''
    logging.info("Parsing trace...")
    # Assuming every task just have one thread
    constants.TRACE_NAME = trace[trace.rfind("/")+1:]
    callstacks_pool, nranks=get_callstacks(
            trace=trace, 
            level=level, 
            image_filter=image_filter,
            metric_types=in_mpi_events,
            burst_info=True)
    app_time = get_app_time(trace)
    constants.TOTAL_TIME = app_time
    logging.debug("{0} ns total trace time.".format(app_time))            

    ''' 2. Getting callstack metrics '''
    logging.info("Reducing information...")
    ribar = ProgressBar("Updating points", len(callstacks_pool))
    ribar.show()

    for callstack in callstacks_pool:
        callstack.in_program_order = arguments.in_program_order
        callstack.calc_reduce_info()
        ribar.progress_by(1)
        ribar.show()

    ''' 3. Filtering below delta '''
    logging.info("Filtering callstacks...")
    fcallstacks_pool=filter(
            lambda x: x.is_above_delta(app_time, arguments.bottom_bound[0]),
            callstacks_pool)
    logging.debug("Reduced from {0} to {1}".format(
        len(callstacks_pool), len(fcallstacks_pool)))
    logging.info("Done")

    if len(fcallstacks_pool) == 0:
        logging.info("All callsacks has been filtered.")
        exit(0)


    ''' 4. Callstacks to delta mapping '''
    logging.info("Callstacks delta classification...")
    if not arguments.use_cplex:
        logging.debug("Calculating delta by mean of heuristics.")
        assert False, "use --cplex"
    else:
        logging.debug("Calculating delta by mean of CPLEX.")
        deltas = calcule_deltas_cplex(fcallstacks_pool,app_time,
                arguments.bottom_bound[0],
                arguments.delta_accuracy[0],
                arguments.cplex_input[0])

        logging.debug("{0} super-loops detected".format(len(deltas)))
    logging.info("Done")


    ''' 5. Clustering '''
    logging.info("Performing clustering...")
    clusters_pool,plot_thread=clustering(fcallstacks_pool, arguments.show_clustering, 
            app_time, deltas, arguments.bottom_bound[0])

    for cluster in clusters_pool:
        cluster.run_loops_generation()

    logging.debug("{0} clusters detected".format(len(clusters_pool)))

    for cl in clusters_pool:
        logging.debug("Cluster {0} have {1} loops".format(
            cl.cluster_id,
            len(cl.loops)))
        for l in cl.loops:
            logging.debug(" -- {0}:{1} {2} iterations".format(
                    cl.cluster_id, l._id, l.original_iterations))
    logging.info("Done")


    ''' 6. Merging clusters '''
    logging.info("Merging clusters...")
    top_level_clusters = merge_clusters(clusters_pool)
    logging.info("Done")


    ''' 7. Reducing callstacks '''
    logging.info("Postprocessing callstacks...")
    for cluster_obj in top_level_clusters:
        for loop_obj in cluster_obj.loops:
            logging.debug("-- Postprocessing loop {0}:{1}".format(
                loop_obj.cluster_id,
                loop_obj._id))
            loop_obj.compact_callstacks(callstacks_pool)
            loop_obj.group_into_conditional_rank_blocks()
            loop_obj.callstack_set_owner_loop()

    callstacks_pool = filter(lambda x: x.repetitions[x.rank] > 1, 
            callstacks_pool)
    logging.info("Done")

    ''' 8. Derivating metrics '''
    logging.info("Derivating metrics")
    for callstack in callstacks_pool:
        callstack.calc_metrics()
    logging.info("Done")


    ''' 9. Generating pseudo-code '''
    for cs in callstacks_pool:
        last_line = cs.calls[0].line
        last_file = cs.calls[0].call_file
        cs.calls[0].line = 0
        cs.calls[0].call_file = ""
        for c in cs.calls[1:]:
            auxl = c.line
            c.line = last_line
            last_line = auxl
            auxf = c.call_file
            c.call_file = last_file
            last_file = auxf

    logging.info("Generating pseudocode...")
    logging.debug("Top level clusters:")
    for cl in top_level_clusters:
        logging.debug("-- CLUSTER {0}".format(cl.cluster_id))

    from console_gui import console_gui
    from html_gui import html_gui

    if arguments.html_output:
        gui_class = html_gui
    else:
        gui_class = console_gui

    # Show burst info and only MPI are False by default
    pc = pseudocode(top_level_clusters, nranks, False, gui_class, False)
    pc.beautify()
    pc.generate()

    logging.info("Done...")

    #''' 10. Show GUI '''
    #print
    #pc.show()

    ''' 11. Start interactive shell '''
    sds = sdshell()
    sds.set_trace(trace)
    sds.set_pseudocode(pc)
    sds.set_clustering_thread(plot_thread)
    sds.cmdloop()

    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
