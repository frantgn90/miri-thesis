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

        for rank in ranks:
            callstacks = filter(lambda x: x.rank == rank, self.callstacks)
            aliasing_detector=tmatrix.from_callstacks_obj(callstacks)

            if aliasing_detector.aliased():
                callstack_parts = aliasing_detector.get_subloops()
                subloops = [loop(callstacks=x) for x in callstack_parts]
                ranks_subloops.append(subloops)
            else:
                ranks_loops.append(loop(callstacks=callstacks))

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

            for i in range(len(max(ranks_subloops))):
                loops_to_merge = []
                for subloops in ranks_subloops:
                    if len(subloops) > i: loops_to_merge.append(subloops[i])

                merged_ranks_loop = self.__ranks_level_merge(loops_to_merge)

                self.loops.append(merged_ranks_loop)
                self.nloops += 1
        else:
            assert False, "Not managed situation."

        self.loops_generation_done = True
   
    def merge(self, other):
        assert len(self.loops) == 1, "Other case no implemented ({0})".format(len(self.loops))
        assert self.get_interarrival_median() > other.get_interarrival_median()

        self.loops[0].merge_with_subloop(other.loops)
        self.nmerges+=1

    def get_parent(self):
        return self._id.split(".")[0]

    def get_interarrival_median(self):
        medians = map(lambda x: x.get_instants_dist_median(), self.callstacks)
        return numpy.mean(medians)
    
    def get_interarrival_mean(self):
        medians = map(lambda x: x.get_instants_dist_mean(), self.callstacks)
        return numpy.mean(medians)

    def is_subloop(self, other):
        if len(self.loops) > 1:
            logging.warn("TODO: When there is more than one loop to what loop is subloop"\
                    " must be decided.")
            return False
        else:
            return self.loops[0].is_subloop(other.loops[0])

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

