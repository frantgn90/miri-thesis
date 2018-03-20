#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import logging
import numpy
import random
import constants
from delta_calculation import get_cost


class call(object):
    def __init__(self, line, call, call_file, callstack):
        self.call=call
        self.line=int(line)
        self.my_callstack = callstack
        self.call_file = call_file
        self.mpi_call = "MPI_" in call
        self.mpi_call_coll = self.call in [
                "MPI_Barrier",
                "MPI_Bcast",
                "MPI_Gather",
                "MPI_Gatherv",
                "MPI_Scatter",
                "MPI_Scatterv",
                "MPI_Allgather",
                "MPI_Allgatherv",
                "MPI_Alltoall",
                "MPI_Alltoallv",
                "MPI_Reduce",
                "MPI_Allreduce",
                "MPI_Reduce_scatter",
                "MPI_Scan"]

        # This variable is needed for the console_gui
        # it defines if the name of this call should be printed
        # or just the line
        self.print_call_name = True
        self.print_call = True

    def get_signature(self):
        return "{0}{1}".format(
                self.call, 
                str(self.line))

    def __eq__(self, other):
        if other == None:
            return False
        else:
            return  self.call==other.call and \
                    self.line == other.line and \
                    not self.mpi_call


    def __str__(self):
        val = "{0} ({1})".format(self.call, self.line)
        return val

class callstack(object):
    def __init__(self, rank, instant, calls):
        self.common_with_prev = None
        self.rank=rank
        self.repetitions={}
        self.repetitions[self.rank]=1
        self.instants=[int(instant)]
        self.iteration_cycles=[]
        self.iteration_cycles_mean=None
        self.instants_distances=[]
        self.instants_distances_mean=None
        self.instants_distances_median=None
        self.delta=None
        self.private_delta=None
        self.delta_cluster=None
        self.cluster_id=None
        self.compacted_ranks=[rank]
        self.condition_level = None
        self.reduced=False
        self.calls=calls
        self.metrics = {}
        self.burst_metrics = {}
        self.partner = set()
        self.compacted_partner = []
        self.metrics[self.rank] = {
                "mpi_duration":0,
                "mpi_msg_size":0}
        self.burst_metrics[self.rank] = {
                "burst_duration":0}
        self.in_program_order = True
        self.my_loop = None

        self.dicts_to_merge = [
                self.metrics,
                self.burst_metrics]

        for call in calls:
            call.my_callstack = self
        signature=""
        for call in self.calls:
            signature += call.get_signature()
        
        self.signature = str(self.rank)+"#"+signature
        self.loop_info = None
        self.already_with_size = 1

    @classmethod
    def empty(cls):
        return cls(0,0,[])

    @classmethod
    def from_trace(cls, rank, instant, lines, calls, files):
        assert len(lines)==len(calls), "#lines and #calls must be equal."
        if len(lines) == 0:
            return None

        calls_obj = []
        for i in range(0, len(lines)):
            calls_obj.append(call(int(lines[i]), calls[i], files[i], None))

        return cls(rank, instant, calls_obj)

    def loop_id(self):
        res = ""
        for loopid in self.loop_info:
            res += str(loopid)
        return res[:-1]

    def with_loop_info(self):
        if self.loop_info == None:
            return False
        return len(self.loop_info) > 0

    def add_mpi_msg_size(self,size):
        if self.repetitions[self.rank] == 1:
            self.metrics[self.rank]["mpi_msg_size"] = size
        else:
            self.metrics[self.rank]["mpi_msg_size_merged"][self.already_with_size] = size
            self.already_with_size += 1

    def set_partner(self, new_partner):
        if not new_partner in self.partner:
            self.partner.add(new_partner)
            self.compacted_partner.append((self.rank, self.partner))

    def get_instants(self):
        return self.instants

    def get_hash(self):
        return self.signature_hash

    def get_end_instants(self):
        return [sum(x) for x in zip(self.instants, 
            self.metrics[self.rank]["mpi_duration_merged"])]

    def get_all_ranks(self):
        return set(self.compacted_ranks)

    def get_line_at_level(self, level):
        return self.calls[level].line

    def get_signature(self):
        #signature=""
        #for call in self.calls:
        #    signature += call.get_signature()
        #return str(self.rank)+"#"+signature
        return self.signature

    def merge(self, other):
        ''' This merging is for merging different repetitions of the same '''
        ''' callstack so same path and same rank '''
        assert self.reduced == False
        assert self.get_signature() == other.get_signature()
        self.repetitions[self.rank]+=1
        self.instants.extend(other.instants)
        self.iteration_cycles.extend(other.iteration_cycles)
        self.partner.update(other.partner)
        
        for self_dtomerge, other_dtomerge in \
                zip(self.dicts_to_merge,other.dicts_to_merge):
            merged_metrics = {}
            for key in self_dtomerge[self.rank]:
                if "_merged" in key: continue
                # Some HWC could be present in one MPI call but not
                # in other. 
                if not key in other_dtomerge[other.rank]: continue

                mkey = key + "_merged"
                if mkey in self_dtomerge[self.rank]:
                    self_dtomerge[self.rank][mkey].append(
                            other_dtomerge[other.rank][key])
                elif not mkey in merged_metrics:
                    merged_metrics.update({
                        mkey:[self_dtomerge[self.rank][key],
                            other_dtomerge[other.rank][key]]})
                else:
                    merged_metrics[mkey].append(
                            other_dtomerge[self.rank][key])

            self_dtomerge[self.rank].update(merged_metrics)
 
    def compact_with(self, other):
        ''' Diverge from previous call in the sense this merge procedure is for the '''
        ''' same path but different ranks '''
        assert self.get_signature().split("#")[1:] == other.get_signature().split("#")[1:]
        assert self.rank != other.rank
        self.compacted_ranks.append(other.rank)
        self.metrics[other.rank] = other.metrics[other.rank]
        self.burst_metrics[other.rank] = other.burst_metrics[other.rank]
        self.repetitions[other.rank] = other.repetitions[other.rank]

        new_partner_pair = (other.rank, other.partner)
        self.compacted_partner.append(new_partner_pair)

    def calc_reduce_info(self):
        self.reduced=True
        if self.repetitions[self.rank] == 1: return

        self.instants.sort()
        self.instants_distances=self.__get_distances(self.instants)
        self.instants_distances_median=numpy.median(self.instants_distances)
        self.instants_distances_mean=numpy.mean(self.instants_distances)
        self.iteration_cycles_mean=numpy.mean(self.iteration_cycles)

        for dtomerge in self.dicts_to_merge:
            for rank in dtomerge:
                rank_calc_metrics={}
                keys_to_remove = [] # For memory footprint purposes
                for key,val in dtomerge[rank].items():
                    if not "merged" in key: continue

                    mean_key = key + "_mean"
                    stdev_key = key + "_stdev"
                    sum_key = key + "_sum"
                    perc_key = key + "_percent"

                    rank_calc_metrics.update({
                        mean_key: numpy.mean(val),
                        stdev_key: numpy.std(val),
                        sum_key: sum(val),
                        perc_key: sum(val)/constants.TOTAL_TIME*100
                    })
                    if key != "mpi_duration_merged":
                        keys_to_remove.append(key)
                dtomerge[rank].update(rank_calc_metrics)

                for rk in keys_to_remove:
                    del dtomerge[rank][rk]


    def calc_metrics(self):
        assert self.repetitions[self.rank] > 1
    
        for dtomerge in self.dicts_to_merge:
            global_results = {}
            for rank in dtomerge:
                for key,val in dtomerge[rank].items():
                    if key == "mpi_duration_merged":
                        continue
                    gkey = "global_"+key

                    if not gkey in global_results:
                        global_results.update({gkey:val})
                    else:
                        global_results[gkey] += val

            mean_of = len(self.compacted_ranks)
            global_results = list(map(lambda it: (it[0],(it[1]/mean_of)), global_results.items()))
            dtomerge.update(global_results)

    def is_above_delta(self, delta, total_time):
        if self.repetitions[self.rank] == 1: return False
        cost=get_cost(self.repetitions[self.rank], 
                total_time, 
                self.instants_distances_mean, 
                delta)
        return cost > 0

    def set_private_delta(self, total_time):
        self.private_delta = (self.repetitions[self.rank]*self.instants_distances_mean)/total_time

    def get_instants_dist_median(self):
        return numpy.median(self.instants_distances)

    def get_instants_dist_mean(self):
        return numpy.mean(self.instants_distances)

    def same_flow(self, other):
        return self.get_signature().split("#")[1] == \
                other.get_signature().split("#")[1]

    def get_call_of_func(self, func_name):
        for call_obj in self.calls:
            if call_obj.call == func_name:
                return call_obj
 
    def __get_distances(self, times):
        dist=[]
        for i in range(1,len(times)):
            dist.append(times[i]-times[i-1])
        return dist
       
    def __eq__(self, other):
        return self.get_signature() == other.get_signature()

    def __lt__(self, other):
        #from loop import loop
        #if type(other) == loop:
        #    other = other.get_first_callstack()
       
        assert self.reduced == True and other.reduced == True

        if not self.in_program_order:
            return self.instants[0] < other.instants[0]
        else:
            for call_i in range(min(len(self.calls), len(other.calls))):
                if not self.calls[call_i] == other.calls[call_i]:
                    #if not self.calls[call_i].call == other.calls[call_i].call:
                    #    logging.warn("Same code line jumps to more than one"\
                    #            " target locations. Assuming arbitrary order.")
                    return self.calls[call_i].line < other.calls[call_i].line

    def __gt__(self, other):
        assert self.reduced == True and other.reduced == True

        if self.in_program_order:
            return self.instants[0] > other.instants[0]
        else:
            for call_i in range(min(len(self.calls), len(other.calls))):
                if self.calls[call_i] != other.calls[call_i]:
                    assert self.calls[call_i].call == other.calls[call_i].call
                    return self.calls[call_i].line > other.calls[call_i].line
                    
    def __le__(self, other):
        assert self.reduced == True and other.reduced == True

        if not self.in_program_order:
           return self.instants[0] <= other.instants[0]
        else:
            for call_i in range(min(len(self.calls), len(other.calls))):
                if self.calls[call_i] != other.calls[call_i]:
                    assert self.calls[call_i].call == other.calls[call_i].call
                    return self.calls[call_i].line <= other.calls[call_i].line
            
    def __ge__(self, other):
        assert self.reduced == True and other.reduced == True

        if not self.in_program_order:
            return self.instants[0] >= other.instants[0]
        else:
            for call_i in range(min(len(self.calls), len(other.calls))):
                if self.calls[call_i] != other.calls[call_i]:
                    assert self.calls[call_i].call == other.calls[call_i].call
                    return self.calls[call_i].line >= other.calls[call_i].line
            
    def __and__(self, other):
        result = []
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] == other.calls[call_i]:
                result.append(self.calls[call_i])
            else:
                break

        result = callstack(0, 0, result)
        if len(result) > 0:
            result.loop_info = self.loop_info
            result.rank = self.rank
            result.repetitions = self.repetitions
            result.instants = self.instants
            result.instants_distances = self.instants_distances
            result.instants_distances_mean = self.instants_distances_mean
            result.instants_distances_median = self.instants_distances_median
            result.delta = self.delta
            result.cluster_id = self.cluster_id
            result.compacted_ranks = self.compacted_ranks
            result.condition_level = self.condition_level
            result.reduced = self.reduced
            result.metrics = self.metrics
            result.burst_metrics = self.burst_metrics
            result.common_with_prev = self.common_with_prev
            result.my_loop = self.my_loop
            result.partner = self.partner
            result.compacted_partner = self.compacted_partner

        return result

    def __sub__(self, other):
        result = []
        for s_call in self.calls:
            if not s_call in other.calls:
                result.append(s_call)

        result = callstack(0, 0, result)
        if len(result) > 0:
            result.loop_info = self.loop_info
            result.rank = self.rank
            result.repetitions = self.repetitions
            result.instants = self.instants
            result.instants_distances = self.instants_distances
            result.instants_distances_mean = self.instants_distances_mean
            result.instants_distances_median = self.instants_distances_median
            result.delta = self.delta
            result.cluster_id = self.cluster_id
            result.compacted_ranks = self.compacted_ranks
            result.condition_level = self.condition_level
            result.reduced = self.reduced
            result.metrics = self.metrics
            result.burst_metrics = self.burst_metrics
            result.common_with_prev = self.common_with_prev
            result.my_loop = self.my_loop
            result.partner = self.partner
            result.compacted_partner = self.compacted_partner

        return result

        #common_len = len(self & other)
        #self.calls = self.calls[common_len:]
        #return self

    def __add__(self, other):
        calls = self.calls
        calls.extend(other.calls)

        result = callstack(0,0, calls)

        if len(result) > 0:
            result.loop_info = self.loop_info
            result.rank = self.rank
            result.repetitions = self.repetitions
            result.instants = self.instants
            result.instants_distances = self.instants_distances
            result.instants_distances_mean = self.instants_distances_mean
            result.instants_distances_median = self.instants_distances_median
            result.delta = self.delta
            result.cluster_id = self.cluster_id
            result.compacted_ranks = self.compacted_ranks
            result.condition_level = self.condition_level
            result.reduced = self.reduced
            result.metrics = self.metrics
            result.burst_metrics = self.burst_metrics
            result.common_with_prev = self.common_with_prev
            result.my_loop = self.my_loop
            result.partner = self.partner
            result.compacted_partner = self.compacted_partner

        return result

    def __getitem__(self, key):
        return self.calls[key]

    def __len__(self):
        return len(self.calls)
         
    def __str__(self):
        if self.instants_distances_mean is None:
            iit_mean = None
        else:
            iit_mean = round(self.instants_distances_mean,2)

        if self.instants_distances_median is None:
            iit_median = None
        else:
            iit_median = round(self.instants_distances_median,2)

        val = "[R {0}][IT {1}][IIT {2}|{3}]\n".format(
                self.compacted_ranks, 
                self.repetitions[self.rank],
                iit_mean,
                iit_median)
        for call in self.calls:
            val += "{0}({1}) ".format(call.call, call.line)
        return val

    def __delitem__(self, index):
        del self.calls[index]
