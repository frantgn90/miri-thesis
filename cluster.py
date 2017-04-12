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
    def __init__(self, cluster_id, ranks, cluster, merged_loop):
        self._id=cluster_id
        self._merges=0
        self._first_line=0
        self._ranks=ranks
        self._cluster=cluster
        self._time_mean = self.__time_mean_m()
        self._time_median = self.__time_median_m()
        self._times = self.__times_m()
        self._delta = self._cluster[0][self._cluster[0].keys()[0]]["delta"]
        
        self._merged_rank_loops = merged_loop
        self._first_line = merged_loop.getFirstLine()

        for callstack in self._cluster:
            cs = callstack.keys()[0]
            data = callstack[cs]   
            assert data["delta"] == self._delta

    @classmethod
    def initCluster(cls, cluster_id, cluster, ranks):
        ranks_loops=[]
        ranks_subloops=[]
        for rank in range(ranks):
            # Filter by rank
            filtered = filter(
                    lambda x: int(x[x.keys()[0]]["rank"]) == rank, cluster)
            
            if len(filtered) > 0:
                cluster_tmatrix = tmatrix.fromCallstackList(filtered)

                # There are not subloops behaving equal
                if not cluster_tmatrix.isTransformed(): # or True:
                    logging.debug("{0} cluster generates new loop for rank {1}."
                            .format(cluster_id, rank))

                    ranks_loops.append(loop(
                        tmat=cluster_tmatrix.getMatrix(), 
                        cstack=cluster_tmatrix.getCallstacks(),
                        rank=rank))
                else:
                    partitions = cluster_tmatrix.getPartitions()

                    logging.debug("{0} cluster: detected {1} subloops behaving equal"\
                            " so clustering have not differentiate them."\
                            " Solving...")

                    subloops=[]
                    for i in range(len(partitions)):
                        subloops.append(
                            loop(tmat=partitions[i].getMatrix(), 
                                 cstack=partitions[i].getCallstacks(),
                                 rank=rank))
                    ranks_subloops.append(subloops)
            else:
                logging.debug("{0} cluster have not calls for rank {1}"
                        .format(cluster_id, rank))

        if len(ranks_loops) > 0:
            logging.debug("{0} cluster merging loops".format(cluster_id))
            merged_rank_loop = cls.__ranks_level_merge(ranks_loops)
            logging.debug("All partial loops merged into {0} iterations loop."
                .format(merged_rank_loop._iterations))

            return [cls(cluster_id, ranks, cluster, merged_rank_loop)]

        elif len(ranks_subloops) > 0:
        
            # Get max lenght
            max_len=0
            for rank_sl in ranks_subloops:
                if len(rank_sl) > max_len: max_len = len(rank_sl)

            clusters=[]
            clcount=1
            for i in range(max_len):
                to_merge = []
                for rank_sl in ranks_subloops:
                    if i < len(rank_sl):
                        to_merge.append(rank_sl[i])

                merged_ranks_loop = cls.__ranks_level_merge(to_merge)

                # Reconstructing partial raw cluster
                # TODO: Im sure there is a better way to do so
                
                partial_ranks = map(lambda x: int(x),merged_ranks_loop.getAllRanks())
                partial_cluster=[]

                for cs in merged_ranks_loop._cstack:
                    for call in cluster:
                        if call.keys()[0] == cs:
                            partial_cluster.append(call)

                clusters.append(
                        cls("{0}.{1}".format(cluster_id, clcount), 
                            partial_ranks, 
                            partial_cluster, 
                            merged_ranks_loop))
                clcount+=1

            return clusters
        else:
            assert False, "Not managed situation."

    @classmethod
    def __ranks_level_merge(cls, ranks_loops):
        for i in range(1, len(ranks_loops)):
            ranks_loops[0].merge(ranks_loops[i])
        assert ranks_loops[0]._iterations > 1
        return ranks_loops[0]
 
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
                .str(0,0,[])
                #.str(0, self._merged_rank_loops._loopdeph)
        pseudocode="\n[ClusterID={0}; Expains={1}%]\n{2}".format(\
                self._id, self._delta*100, pseudocode)
        return pseudocode

        
    def getLoop(self):
        return self._merged_rank_loops

    def getnMerges(self):
        return self._merges

    def getFirstLine(self):
        return self._first_line

    def is_subloop(self,cluster):
        return self.getParent() != cluster.getParent()\
                and self._merged_rank_loops.is_subloop(cluster.getLoop())

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

    def getParent(self):
        return self._id.split(".")[0]

