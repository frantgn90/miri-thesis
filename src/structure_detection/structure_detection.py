#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, os
import numpy

import logging
import argparse, argcomplete

from trace import trace
#from trace_parsing import *
from callstack_distribution import *
from delta_calculation import *
from clustering import *
from utilities import *
from flowgraph import flowgraph
from pseudocode import pseudocode
from cluster import merge_clusters
from sdshell import sdshell
import constants
from profiler import profiler

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

    parser.add_argument("--in-time-order",
            action="store_true",
            help="Whether you want pseudocode callstacks in time order"\
                    " or in program order",
            dest="in_time_order")

    parser.add_argument("--burst-info",
            action="store_true",
            help="Whether you want burst info be showed or not",
            dest="show_burst_info")


    argcomplete.autocomplete(parser)
    arguments = parser.parse_args(args=argv[1:])

    tracename = arguments.prv_trace[0]
    ri = arguments.nrandits
    tmp_files_dir = arguments.tmp_files[0]
    numeric_level = getattr(logging, arguments.log_level[0].upper(), None)
    bottom_bound = arguments.bottom_bound[0]

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

    ''' Workflow -----------------------------------------------------------'''
    constants.TRACE_NAME = tracename[tracename.rfind("/")+1:]
    wfprof = profiler({
        1:"Trace parsing and cs reduce",
        2:"Filter (below {0})".format(arguments.bottom_bound[0]),
        3:"Phase recognition",
        4:"Clustering",
        5:"Clusters merging",
        6:"Inter-rank reduction",
        7:"Statistics generation",
        8:"Pseudocode generation"
    })

    ''' 1. Parsing trace -------------------------------------------------- '''
    logging.info("Parsing trace..."); 
    wfprof.step_init(1)
    traceobj = trace(tracename)
    callstacks_pool = traceobj.parse(1)
    constants.TOTAL_TIME = traceobj.total_time
    wfprof.step_fini(1)

    logging.info("{0} ranks with {1} MPI calls".format(traceobj.get_ntasks(), 
        [len(x) for x in callstacks_pool]))

    ''' 3. Filtering below delta ------------------------------------------ '''
    logging.info("Filtering callstacks below {0}.".format(bottom_bound))
    wfprof.step_init(2)
    for rank in traceobj.get_taskids():
        callstacks_pool[rank]=dict(filter(lambda x: x[1].is_above_delta(
            traceobj.total_time, 
            bottom_bound), callstacks_pool[rank].items()))
    wfprof.step_fini(2)

    if len(callstacks_pool) == 0:
        logging.info("All callsacks has been filtered.")
        exit(0)

    logging.info("Reduced to {0} callstacks".format(
        [len(x) for x in callstacks_pool]))

    # Take into account just the parsed ranks (in case partial files are used)
    plane_cs_pool = []
    for rank in traceobj.get_taskids():
        plane_cs_pool.extend(list(callstacks_pool[rank].values()))

    # Just for historical naming...
    callstacks_pool = plane_cs_pool

    # REMOVE!!!!!! This is when application is extrae statically linked
    for cs in callstacks_pool:
        del cs.calls[-2]

    ''' 4. Phases recognition --------------------------------------------- '''
    logging.info("Phases recognition...")
    wfprof.step_init(3)
    deltas = calcule_deltas_clustering(callstacks_pool, constants.TOTAL_TIME)
    logging.info("{0} deltas detected: {1}".format(len(deltas), deltas))
    wfprof.step_fini(3)
    logging.info("Done")

    ''' 5. Clustering ----------------------------------------------------- '''
    logging.info("Performing clustering...")
    wfprof.step_init(4)

    clusters_pool,plot_thread=clustering(callstacks_pool, 
            arguments.show_clustering, 
            constants.TOTAL_TIME, deltas, arguments.bottom_bound[0])

    for cluster in clusters_pool:
        cluster.run_loops_generation()
    logging.debug("{0} clusters detected".format(len(clusters_pool)))
    wfprof.step_fini(4)

    for cl in clusters_pool:
        logging.debug("Cluster {0} have {1} loops".format(cl.cluster_id,
            len(cl.loops)))
        for l in cl.loops:
            logging.debug(" -- {0}:{1} {2} iterations".format(cl.cluster_id, 
                l._id, l.original_iterations))
    logging.info("Done")

   

    ''' 6. Merging clusters ----------------------------------------------- '''
    logging.info("Merging clusters...")
    wfprof.step_init(5)
    top_level_clusters = merge_clusters(clusters_pool)
    wfprof.step_fini(5)
    logging.info("Done")

    ''' 7. Inter-rank reduction ------------------------------------------- '''
    logging.info("Postprocessing callstacks...")
    wfprof.step_init(6)
    for cluster_obj in top_level_clusters:
        for loop_obj in cluster_obj.loops:
            logging.debug("-- Postprocessing loop {0}:{1}".format(
                loop_obj.cluster_id,
                loop_obj._id))
            loop_obj.compact_callstacks(callstacks_pool)
            loop_obj.group_into_conditional_rank_blocks()
            loop_obj.callstack_set_owner_loop()

    callstacks_pool = list(filter(lambda x: x.repetitions[x.rank] > 1, 
            callstacks_pool))

    wfprof.step_fini(6)
    logging.info("Done")

    ''' 7.1. Clustering sanity check --------------------------------------'''
    ''' This sanity check requires to compile the binary with extraecc/    '''
    ''' extraecxx/extraefc for automatic loops monitoring. These monitors  '''
    ''' will provide us information about on what loop we are.             '''
    ''' If clustering went right, all calls on same cluster will be from   '''
    ''' the same loop, so if not it is an error and tuning of clustering   '''
    ''' parameters should be explored.                                     '''
    ''' If no loop-id information is available in trace, this step is not  '''
    ''' usable.                                                            '''
    ''' -------------------------------------------------------------------'''
 
    ''' Testing for aliasing '''
    for cluster in clusters_pool:
        if not cluster.check_loop_id():
             logging.error("Missarrangement of callstacks for cluster {0}"
                     .format(cluster.cluster_id))
        else:
            logging.debug("Nice clustering for cluster {0}"
                    .format(cluster.cluster_id))


    #for cluster in clusters_pool:
    #    res = cluster.check_structure()
    #    if res:
    #        print ("Cluster {0}: OK".format(cluster.cluster_id))
    #    else:
    #        print ("Cluster {0}: Error".format(cluster.cluster_id))


    ''' 8. Derivating metrics --------------------------------------------- '''
    logging.info("Derivating metrics")
    wfprof.step_init(7)
    for callstack in callstacks_pool:
        callstack.calc_metrics()
    wfprof.step_fini(7)
    logging.info("Done")

    ''' 9. Generating pseudo-code ----------------------------------------- '''
    wfprof.step_init(8)
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
        logging.debug("-- Cluster {0} ({1} loops)".format(cl.cluster_id, 
            cl.nloops))

    from console_gui import console_gui
    from html_gui import html_gui

    if arguments.html_output:
        gui_class = html_gui
    else:
        gui_class = console_gui

    # Show burst info and only MPI are False by default
    pc = pseudocode(top_level_clusters, traceobj.get_taskids(), 
            False, gui_class, False)
    pc.beautify()
    pc.generate()

    wfprof.step_fini(8)
    logging.info("Done...")

    wfprof.show_statistics()

    ''' 11. Start interactive shell --------------------------------------- '''
    sds = sdshell()
    sds.set_trace(tracename)
    sds.set_pseudocode(pc)
    sds.set_clustering_thread(plot_thread)
    sds.cmdloop()

    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
