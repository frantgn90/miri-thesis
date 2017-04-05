#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, random, logging
import numpy as np
import constants
from temp_matrix import tmatrix
from loop import loop

import pdb

class cluster (object):
    def __init__(self, cluster_id, cluster, ranks):
        self._id=cluster_id
        self._merges=0
        self._first_line=0
        self._ranks=ranks
        self._cluster=cluster
        self._time_mean = self.__time_mean_m()
        self._time_median = self.__time_median_m()
        self._times = self.__times_m()
        
        self._delta = self._cluster[0][self._cluster[0].keys()[0]]["delta"]
        for callstack in self._cluster:
            cs = callstack.keys()[0]
            data = callstack[cs]
            
            assert data["delta"] == self._delta

        ranks_loops=[]
        for rank in range(self._ranks):
            # Filter by rank
            filtered = filter(
                    lambda x: int(x[x.keys()[0]]["rank"]) == rank, 
                    self._cluster)
            
            if len(filtered) > 0:
                self._tmatrix = tmatrix.fromCallstackList(filtered)

                # There are not subloops behaving equal
                if not self._tmatrix.isTransformed(): # or True:
                    logging.debug("{0} cluster generates new loop for rank {1}."
                            .format(self._id, rank))

                    ranks_loops.append(loop(
                        tmat=self._tmatrix.getMatrix(), 
                        cstack=self._tmatrix.getCallstacks(),
                        rank=rank))
                else:
                    partitions = self._tmatrix.getPartitions()

                    logging.debug("{0} cluster: detected {1} subloops behaving equal"\
                            " so clustering have not differentiate them."\
                            " Solving...")

                    subloops=[]
                    for i in range(len(partitions)):
                        subloops.append(
                            loop(
                                tmat=partitions[i].getMatrix(), 
                                cstack=partitions[i].getCallstacks(),
                                rank=rank))

                        assert False, "Hoy no... mañana!"
                    #merged_loop = self.__loops_level_merge(subloops)
                    #ranks_loops.extend(subloops)

        # Ranks merge level
        logging.debug("{0} cluster merging loops".format(self._id))
        self.__ranks_level_merge(ranks_loops)

  
    def __time_mean_m(self):
        total_time=0
        for callstack in self._cluster:
            values = callstack[callstack.keys()[0]]
            total_time += values["time_mean"]

        return total_time/len(self._cluster)
    
    def __time_median_m(self):
        total_time=0
        for callstack in self._cluster:
            values = callstack[callstack.keys()[0]]
            total_time += values["time_median"]

        return total_time/len(self._cluster)

    def __times_m(self):
        max_times = 0
        for callstack in self._cluster:
            values = callstack[callstack.keys()[0]]
            if values["times"] > max_times:
                max_times = values["times"]

        return max_times
    
    def getPeriod(self):
        return self._time_mean

    def getTimesMedian(self):
        return self._time_median

    def getOccurrences(self):
        return self._times

    def str(self):
        pseudocode, dummy=self._merged_rank_loops\
                .str(0,0)
                #.str(0, self._merged_rank_loops._loopdeph)
        pseudocode="\n[ClusterID={0}; Expains={1}%]\n{2}".format(\
                self._id, self._delta*100, pseudocode)
        return pseudocode

        
    def __loops_level_merge(self, loops):
        # They are not subloops between them
        #assert False, "It is not developed yet."

        for i in range(1,len(loops)):
            loops[0].merge(loops[i])
        return loops[0]

    def __ranks_level_merge(self, ranks_loops):
        for i in range(1, len(ranks_loops)):
            ranks_loops[0].merge(ranks_loops[i])

        assert ranks_loops[0]._iterations > 1

        self._merged_rank_loops=ranks_loops[0]
        self._first_line = self._merged_rank_loops.getFirstLine()
        
        logging.debug("All partial loops merged into {0} iterations loop."
                .format(self._merged_rank_loops._iterations))

    def getLoop(self):
        return self._merged_rank_loops

    def getnMerges(self):
        return self._merges

    def getFirstLine(self):
        return self._first_line

    def merge(self, ocluster):
        assert(self.getTimesMedian() > ocluster.getTimesMedian())
        #assert(ocluster.getFirstLine() >= self._first_line)

        self._merged_rank_loops.merge_subloop(ocluster.getLoop())
        self._merges+=1

        logging.debug("New loop with {0} iterations merging {1} and {2} clusters"
                .format(self._merged_rank_loops._iterations, self._id, ocluster._id))

    def getRandomIterations(self, n):
        niters = self._merged_rank_loops._iterations
        result = []
        for i in range(n):
            rit=random.randrange(0,niters-1)
            iteration = self._merged_rank_loops.getIteration(0, rit)
            result.append(iteration)

        return result

