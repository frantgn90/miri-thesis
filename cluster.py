#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, random
import numpy as np
import constants
from temp_matrix import tmatrix

import pdb

class cluster (object):
    def __init__(self, cluster, ranks):
        self._merges=0
        self._first_line=0
        self._ranks=ranks
        self._cluster=cluster
        self._time_mean = self.__time_mean_m()
        self._times = self.__times_m()
        
        ranks_loops=[]
        for rank in range(self._ranks):
            # Filter by rank
            filtered=[]
            for cs in self._cluster: 
                k=cs.keys()[0]
                if cs[k]["rank"] == rank: filtered.append(cs)

            if not len(filtered) == 0:
                self._tmatrix = tmatrix(filtered)

                if not self._tmatrix.isTransformed():
                    ranks_loops.append(loop(self._tmatrix, rank))
                else:
                    partitions = self._tmatrix.getPartitions()

                    loops=[]
                    for i in range(len(partitions)):
                        loops.append(loop(partitions[i], rank))

                    self.__loops_level_merge(self, loops)

        # Ranks merge level
        self.__ranks_level_merge(ranks_loops)

    
    def __time_mean_m(self):
        total_time=0
        for callstack in self._cluster:
            values = callstack[callstack.keys()[0]]
            total_time += values["time_mean"]

        return total_time/len(self._cluster)
    

    def __times_m(self):
        total_times=0
        for callstack in self._cluster:
            values = callstack[callstack.keys()[0]]
            total_times += values["times"]

        return total_times/len(self._cluster)
    
    def getPeriod(self):
        return self._time_mean

    def getOccurrences(self):
        return self._times

    def str(self):
        pseudocode, dummy=self._merged_rank_loops\
                .str(0, self._merged_rank_loops._loopdeph)
        return pseudocode

        
    def __loops_level_merge(self, loops):
        assert False, "It is not developed yet."

    def __ranks_level_merge(self, ranks_loops):
        # Merging all ranks with first one

        for i in range(1, len(ranks_loops)):
            ranks_loops[0].merge(ranks_loops[i])

        self._merged_rank_loops=ranks_loops[0]
        self._first_line = self._merged_rank_loops.getFirstLine()
    

    def getLoop(self):
        return self._merged_rank_loops

    def getnMerges(self):
        return self._merges

    def getFirstLine(self):
        return self._first_line

    def merge(self, ocluster):
        self._merges += 1

        # Is it a subloop ?
        assert(ocluster.getOccurrences() > self._times)
        #assert(ocluster.getFirstLine() >= self._first_line)

        subloop = ocluster.getLoop()

        # We have to merge this subloop with our __ranks_level_merge
        # TODO: (??) We need the times of the callstacks!! and the overall time 
        # of the loop in order to fit it in its correct place!!!!
       
        self._merged_rank_loops.mergeS(subloop)
        self._merges+=1

    def getRandomIterations(self, n):
        niters = self._merged_rank_loops._iterations
        result = []
        for i in range(n):
            rit=random.randrange(0,niters-1)
            iteration = self._merged_rank_loops.getIteration(0, rit)
            result.append(iteration)

        return result

