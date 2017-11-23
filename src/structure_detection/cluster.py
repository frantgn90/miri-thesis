#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, random, logging
import numpy

import constants
from temp_matrix import tmatrix
from loop import loop
from utilities import *

class cluster (object):
    def __init__(self, cluster_id):
        # All callstacks in a cluster forms one or more than one loops
        # it will depend on the aliasing analysis
        #
        self.loops = []
        self.nloops = 0
        self.cluster_id=cluster_id
        self.callstacks=[]
        self.loops_generation_done = False
        self.delta = None
        self.nmerges = 0

    def get_first_line(self):
        return self.loops[0].get_first_line()

    def add_callstack(self, callstack):
        assert self.loops_generation_done == False
        assert callstack.cluster_id==self.cluster_id
        self.callstacks.append(callstack)

        if self.delta == None:
            self.delta = callstack.delta
#        else:
#            assert self.delta == callstack.delta

    def run_loops_generation(self):
        ranks = list(set(map(lambda x: x.rank, self.callstacks)))

        # First one loop per rank is done. After the generation step, the 
        # rank merge step is done.
        # 
        ranks_loops=[]

        # If aliasing is detected, every subloop will be an independent loop
        # object. After generation, the cluster is divided into sub-clusters
        #
        ranks_subloops=[]
        loops_id = 0
        for rank in ranks:
            callstacks = filter(lambda x: x.rank == rank, self.callstacks)
            aliasing_detector=tmatrix.from_callstacks_obj(callstacks)

            if aliasing_detector.aliased():
                callstack_parts = aliasing_detector.get_subloops()
                subloops = []
                for x in callstack_parts:
                    new_loop = loop(callstacks=x,id=loops_id)
                    new_loop.cluster_id = self.cluster_id
                    subloops.append(new_loop)
                    loops_id += 1
                ranks_subloops.append(subloops)
            else:
                new_loop = loop(callstacks=callstacks, id=loops_id)
                new_loop.cluster_id = self.cluster_id
                ranks_loops.append(new_loop)
                loops_id += 1

        if len(ranks_loops) > 0:
            self.loops.append(self.__ranks_level_merge(ranks_loops))
            self.nloops = 1
        elif len(ranks_subloops) > 0:
            # Here i am assuming that all subloops of all ranks are related
            # between them in function of the order they appear in the ranks_
            # subloop.
            # ranks_subloops = [ [loop1.1, loop1.2, loop1.3],
            #                    [loop2.1, loop2.2, loop2.3]]
            #                        |        |         |
            #                      merged   merged   merged

            ssubloops = []
            nsubloops = 0
            for i in range(len(max(ranks_subloops))):
                loops_to_merge = []
                for subloops in ranks_subloops:
                    if len(subloops) > i: loops_to_merge.append(subloops[i])

                merged_ranks_loop = self.__ranks_level_merge(loops_to_merge)

                ssubloops.append(merged_ranks_loop)
                nsubloops += 1
#                self.loops.append(merged_ranks_loop)
#                self.nloops += 1

            if aliasing_detector.is_hidden_superloop():
                superloop = loop(callstacks=[], id=-1) # Void loop
                superloop.cluster_id = self.cluster_id
                superloop.iterations = aliasing_detector\
                    .get_hidden_superloop_its()
                superloop.original_iterations = superloop.iterations
                superloop.set_hidden_loop()
                logging.debug("Cluster {0}: Superloop detected ({1} its)"
                        .format(self.cluster_id, superloop.iterations)) 

                for sl in ssubloops:
                    superloop.merge_with_subloop(sl)

                self.loops.append(superloop)
                self.nloops = 1
            else:
                self.loops.extend(ssubloops)
                self.nloops = nsubloops
        else:
            assert False, "Not managed situation."

        self.loops_generation_done = True

    def push_datacond(self, other):
        original_nloops = len(self.loops)
        loops_to_remove = []

        for i in range(len(self.loops)):
            for j in range(len(other.loops)):
                assert not other.loops[j].already_merged
                self_loop_id = self.loops[i].get_str_id()
                other_loop_id = other.loops[j].get_str_id()

                if self.loops[i].hidden_loop:
                    #print "-- {0} loop is hidden_loop".format(self_loop_id)
                    i_loops = self.loops[i].callstack_list
                else:
                    i_loops = [self.loops[i]]

                if other.loops[j].hidden_loop:
                    #print "-- {0} loop is hidden_loop".format(other_loop_id)
                    j_loops = other.loops[j].callstack_list
                else:
                    j_loops = [other.loops[j]]

                #import pdb; pdb.set_trace()
                for i_l in i_loops:
                    for j_l in j_loops:
                        assert type(i_l) == loop
                        assert type(j_l) == loop
                        self_sloop_id = i_l.get_str_id()
                        other_sloop_id = j_l.get_str_id()

                        result = i_l.push_datacondition_callsacks(j_l)
                        #result = self.loops[i].push_datacondition_callsacks(
                        #        other.loops[j])
                        if result == 0:
                            logging.debug("-- LOOP {0} NOT PUSHED to {1}"
                                    .format(self_sloop_id,other_sloop_id))
                        elif result == 1:
                            logging.debug("-- LOOP {0} PUSHED to {1}"
                                    .format(self_sloop_id,other_sloop_id))
                            loops_to_remove.append(self_loop_id) # OJO
                        else:
                            logging.debug("-- LOOP {0} PARTIALLY PUSHED {1}"
                                    .format(self_sloop_id,other_sloop_id))

                # TODO: self_loop_id only have to be removed if all 
                # self_sloop_id have been inverselly merged
                # (for the moment is enough for MG)

        # Removing inverselly merged loops
        self.loops = filter(
            lambda x: not x.get_str_id() in loops_to_remove,
            self.loops)

        if len(self.loops) == original_nloops:
            return 0 # No one loop pushed
        elif len(self.loops) == 0:
            return 1 # All loops pushed
        else:
            return 2 # Some loops pushed

    def merge(self, other):
        assert len(self.loops) > 0
        assert len(other.loops) > 0

        #assert self.get_interarrival_median() > other.get_interarrival_median()
        #assert len(self.loops) == len(other.loops)

        merged = 0

        for l in other.loops:
            if l.already_merged: merged += 1

        loops_to_remove = []
        for i in range(len(self.loops)):
            for j in range(len(other.loops)):
                other_loop_id = other.loops[j].get_str_id()
                self_loop_id = self.loops[i].get_str_id()
                #other_loop_id="{0}.{1}"
                #    .format(other.cluster_id, other.loops[j]._id)
                #self_loop_id="{0}.{1}"
                #    .format(self.cluster_id, self.loops[i]._id)

                if other.loops[j].already_merged == True:
                    logging.debug("-- LOOP {0} already merged"
                            .format(other_loop_id))
                    continue

                logging.debug("-- Try LOOP {0} merge to LOOP {1}".format(
                    other_loop_id, self_loop_id))
                is_subloop = self.loops[i].is_subloop(other.loops[j])

                if is_subloop:
                    n_original_cs = len(self.loops[i])
                    #self.loops[i].push_datacondition_callsacks(other.loops[j])
                    self.loops[i].merge_with_subloop(other.loops[j])

                    if len(self.loops[i]) == 0:
                        logging.debug("-- LOOP {0} MERGED to {1} (Data cond.)"
                            .format(self_loop_id, other_loop_id))
                        loops_to_remove.append(self_loop_id)
                    elif n_original_cs > len(self.loops[i]):
                        logging.debug("-- LOOP {0} PARTIALLY MERGED to {1}"\
                                " ({2}/{3}) (Data cond.)"
                            .format(self_loop_id, other_loop_id, 
                                len(self.loops[i]), n_original_cs))
                    else:
                        logging.debug("-- LOOP {0} MERGED to {1}".format(
                            other_loop_id, self_loop_id))
                        other.loops[j].already_merged = True
                    merged += 1
                else:
                    logging.debug("-- LOOP {0} NOT merged to {1}".format(
                        other_loop_id, self_loop_id))

        # Removing inverselly merged loops
        self.loops = filter(
            lambda x: not x.get_str_id() in loops_to_remove,
            self.loops)

        if merged > 0 and merged < len(other.loops):
            logging.warning("Some loops have not been merged.")
        self.nmerges += 1

        return merged == len(other.loops)

    def get_parent(self):
        return self._id.split(".")[0]

    def get_interarrival_median(self):
        medians = map(
                lambda x: x.get_instants_dist_median(), 
                self.callstacks)
        return numpy.mean(medians)
    
    def get_interarrival_mean(self):
        medians = map(
                lambda x: x.get_instants_dist_mean(), 
                self.callstacks)
        return numpy.mean(medians)

#    def is_subloop(self, other):
#        if len(self.loops) > 1:
#            logging.warn("TODO: When there is more than one loop to" \
#                    " what loop is subloop must be decided.")
#            return False
#        else:
#            return self.loops[0].is_subloop(other.loops[0])

    def __ranks_level_merge(self, ranks_loops):
        for i in range(1, len(ranks_loops)):
            ranks_loops[0].merge(ranks_loops[i])
        assert ranks_loops[0].iterations > 1
        return ranks_loops[0]
 
    def __str__(self):
        title= "Cluster ID = {0:03d}".format(self.cluster_id)
        val  = "Callstacks = {0:03d}\n".format(len(self.callstacks))
        val += "Loops = {0:03d}\n".format(self.nloops)
        val += "Delta = {0}\n".format(self.delta)

        val = pretty_print(val, title)
        for loop in self.loops:
            val += str(loop)
        
        return val

    def __lt__(self, other):
        pass


def merge_clusters(clusters_pool):
    logging.debug("Classifying clusters by delta.")

    cluster_by_delta = {}
    def ___cluster_classification(x):
        delta = x.delta
        if delta in cluster_by_delta: 
            cluster_by_delta[delta].append(x)
        else: 
            cluster_by_delta[delta]=[x]

    map(___cluster_classification, clusters_pool)

    for k,v in cluster_by_delta.items():
        logging.debug("Sorting clusters ({0}) with delta={1}".format(len(v), k))
        v.sort(key=lambda x: x.get_interarrival_mean(), reverse=False)
        logging.debug("Sorted: {0}".format([x.cluster_id for x in v]))

    top_level_clusters=[]
    for delta,clusters in cluster_by_delta.items():
        logging.debug("Merging {0} clusters with delta={1}".format(
            len(clusters),
            delta))

        '''
        First step, look for data condition clusters
        '''
        logging.debug("Reverse merge for data conditions...")
        cluster_to_remove = []
        for i in range(len(clusters)-1,-1,-1):
            for j in range(i-1,-1,-1):
                logging.debug("Try PUSH DATACOND CLUSTER {0} to CLUSTER {1}"
                        .format(clusters[i].cluster_id, clusters[j].cluster_id))

                res = clusters[i].push_datacond(clusters[j])

                if res == 0:
                    logging.debug("CLUSTER {0} NOT PUSHED to {1}".format(
                        clusters[i].cluster_id, clusters[j].cluster_id))
                elif res == 1:
                    logging.debug("CLUSTER {0} PUSHED to {1}".format(
                        clusters[i].cluster_id, clusters[j].cluster_id))
                    cluster_to_remove.append(clusters[i].cluster_id)
                    break
                else:
                    logging.debug("CLUSTER {0} PARTIALLY PUSHED to {1}".format(
                        clusters[i].cluster_id, clusters[j].cluster_id))

        cluster_by_delta[delta] = filter(
                lambda x: not x.cluster_id in cluster_to_remove, 
                cluster_by_delta[delta])
        clusters = cluster_by_delta[delta]
        logging.debug("Reverse merge for data conditions DONE")


        '''
        Second step, merge clusters
        '''
        logging.debug("Actually merging clusters")
        to_remove = []
        for i in range(len(clusters)-1):
            merged=False
            for j in range(i+1,len(clusters)):
                logging.debug("Try MERGE CLUSTER {0} to CLUSTER {1}".format(
                    clusters[i].cluster_id, clusters[j].cluster_id))

                merged = clusters[j].merge(clusters[i])

                if merged:
                    logging.debug("CLUSTER {0} MERGED to {1}".format(
                        clusters[i].cluster_id, clusters[j].cluster_id))
                    break
                else:
                    logging.debug("NOT MERGED")
                           
            if not merged:
                loops_merged = 0
                for l in clusters[i].loops:
                    if l.already_merged: loops_merged += 1
                
                if loops_merged < len(clusters[i].loops):
                    logging.warning("Cluster {0} could not be merged completely" \
                            " ({1}/{2})"
                            .format(clusters[i].cluster_id, 
                                loops_merged, 
                                len(clusters[i].loops)))

        logging.debug("Merging done")
        
        # TODO: When there is some cluster that could not be merged,
        # it has to be included as a top_level_clusters
        top_level_clusters.append(cluster_by_delta[delta][-1])

    return top_level_clusters
