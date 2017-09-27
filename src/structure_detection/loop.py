#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, random, logging
import numpy as np
import copy

import constants
from callstack import callstack
from temp_matrix import tmatrix
from utilities import *

class conditional_rank_block(object):
    def __init__(self, ranks):
        self.ranks = ranks
        self.common_callstack = None
        self.common_with_prev = None
        self.data_condition = False
        self.probability = 0
        self.callstacks = []

    def add_callstack(self, callstack_or_loop):
        set1 = set(self.ranks)
        set2 = set(callstack_or_loop.get_all_ranks())
        is_equal = set1 == set2
        is_subset = set1.issubset(set2) and not is_equal
        is_superset = set1.issuperset(set2) and not is_equal
        is_complement = len(set1.intersection(set2)) == 0

        assert is_subset == False, "Impossible situation."
        assert is_complement == False, "Impossible sitation."
        assert is_equal or is_superset, "Must be equal or a subset."

        # TODO: Look for callstack_or_loop.repetitions < loop iterations
        #
        if is_equal:
            self.callstacks.append(callstack_or_loop)
            return
        elif is_superset:
            if len(self.callstacks) > 0:
                if isinstance(self.callstacks[-1], conditional_rank_block):
                    last_cond_block = self.callstacks[-1]

                    # Let's see if we have a subsubblock or just a subblock
                    #
                    set1 = set(last_cond_block.ranks)
                    set2 = set(callstack_or_loop.get_all_ranks())
                    is_equal = set1 == set2
                    is_subset = set1.issubset(set2) and not is_equal
                    is_superset = set1.issuperset(set2) and not is_equal
                    is_complement = len(set1.intersection(set2)) == 0

                    if is_equal or is_superset:
                        self.callstacks[-1].add_callstack(callstack_or_loop)
                    else:
                        new_cond_block = conditional_rank_block(
                            callstack_or_loop.get_all_ranks())
                        new_cond_block.add_callstack(callstack_or_loop)
                        self.callstacks.append(new_cond_block)
                else:
                    new_cond_block = conditional_rank_block(
                        callstack_or_loop.get_all_ranks())
                    new_cond_block.add_callstack(callstack_or_loop)
                    self.callstacks.append(new_cond_block)
            else:
                new_cond_block = conditional_rank_block(
                        callstack_or_loop.get_all_ranks())
                new_cond_block.add_callstack(callstack_or_loop)
                self.callstacks.append(new_cond_block)
            return
        assert False

    def extracting_callstack_common_part(self):
        # Calculing the common part for subblocks
        #
        for cond_block_obj in self.callstacks:
            if isinstance(cond_block_obj, conditional_rank_block):
                cond_block_obj.extracting_callstack_common_part()

        first_callstack = self.callstacks[0]
        if not isinstance(first_callstack, callstack):
            first_callstack = first_callstack.common_callstack


        # Getting the common callstacks
        #
        for callstack_obj in self.callstacks:
            if not isinstance(callstack_obj, callstack):
                callstack_obj = callstack_obj.common_callstack
            first_callstack &= callstack_obj
        self.common_callstack = first_callstack

        # Removing the common callstacks for callstacks
        #
        for callstack_i in range(len(self.callstacks)):
            if not isinstance(self.callstacks[callstack_i], callstack):
                self.callstacks[callstack_i]\
                        .common_callstack -= self.common_callstack
            else:
                self.callstacks[callstack_i] -= self.common_callstack

    def __str__(self):
        res  = "Ranks: {0}\n".format(self.ranks)
        res += "Common: {0}\n".format(self.common_callstack)
        if len(self.callstacks) > 0:
            res += "***** [CONTENT] *****\n"
            for callstack_obj in self.callstacks:
                if isinstance(callstack_obj, loop):
                    res += "LOOP Ranks:{0} Ncallstacks:{1}\n"\
                            .format(callstack_obj.get_all_ranks(), 
                                    len(callstack_obj.program_order_callstacks))
                elif isinstance(callstack_obj, conditional_rank_block):
                    res += "--- Subblock ---\n"
                    res += str(callstack_obj)
                    res += "--- End subblock ---\n"
                else:
                    res += str(callstack_obj) + "\n"
            res += "*********************\n"
        return res
 

class loop (object):
    def __init__(self, callstacks):
        # Maybe this loop is just an statement under a condition of 
        # other loop
        #
        self.is_condition = False
        self.condition_probability = 0

        # Is the position where the condition of the first callstack is
        #
        self.condition_level = None

        # This loop is made by how many merges
        #
        self.nmerges = 1
        
        # Number of iterations of the loop. The original iterations
        # are needed because number of iterations will change in case
        # this loop was indeed a subloop
        #
        self.iterations = callstacks[0].repetitions
        self.original_iterations = self.iterations

        # Sanity check 1 !!!
        #
#        for callstack in callstacks:
#            assert callstack.repetitions == self.iterations, \
#                    "Loop: Sanity check #1 fail"

        # We have a chain of calls, this variable indicates where
        # in this chain the loop represented by this object is. The way
        # to calculate it is to get just the common part of all the
        # chains
        #
        self.loop_deph = None
        self.common_callstack = None
        
        # Until now, the order of the callstacks were not important
        # but now it is, so lets sort it. The order should be the
        # program order so the line is the parameter to take into account
        self.program_order_callstacks = sorted(callstacks)

        # Main conditional rank block beloging to this loop. The main conditional
        # block is the block that is executed by the same ranks as the loop.
        #
        self.conditional_rank_blocks = None

        logging.debug("New loop with {0} iterations.".format(self.iterations))

    def get_all_ranks(self):
        ranks = []
        for cs in self.program_order_callstacks:
            if isinstance(cs, callstack):
                ranks.extend(cs.get_all_ranks())
            elif isinstance(cs, loop):
                ranks.extend(cs.get_all_ranks())

        return list(set(ranks))
    
    def merge(self, other):
        assert type(other) == loop
        assert other.nmerges == 1

        merged_callstacks = other.program_order_callstacks\
                + self.program_order_callstacks
        self.program_order_callstacks = sorted(merged_callstacks)
        self.nmerges += 1

    def merge_with_subloop(self, other):
        # The difference with the previous merge is that now 'other' is a subloop
        # of ourselfs. So new comparative functions have to be added to this class

        for loop_obj in other:
            loop_obj.iterations /= self.iterations

        merged_subloop = self.program_order_callstacks + other
        self.program_order_callstacks = sorted(merged_subloop)

        i=0
        common_callstack = self.program_order_callstacks[i]
        while isinstance(common_callstack, loop):
            i += 1
            common_callstack = self.program_order_callstacks[i]

    def get_first_line(self):
        if type(self.program_order_callstacks[0]) == loop:
            return self.program_order_callstacks[0].get_first_line()
        else:
            return self.program_order_callstacks[0].calls[0].line


    def get_first_callstack_instants(self):
        if type(self.program_order_callstacks[0]) == loop:
            return self.program_order_callstacks[0].get_first_callstack_instants()
        else:
            return self.program_order_callstacks[0].instants

    def is_subloop(self, other):
        its_bounds = self.get_first_callstack_instants()
        sub_times = other.get_first_callstack_instants()


#        its_bounds = self.program_order_callstacks[0].instants
#        sub_times  = other.program_order_callstacks[0].instants


        last_j = 0
        is_subloop = False

        for i in range(len(its_bounds))[0::2]:
            if i+1 >= len(its_bounds): break
            lower_bound = int(its_bounds[i])
            upper_bound = int(its_bounds[i+1])

            for j in range(last_j, len(sub_times)):
                if int(sub_times[j]) >= lower_bound\
                    and int(sub_times[j]) <= upper_bound:
                    is_subloop = True
                    break
        
        return is_subloop;

    def compact_callstacks(self):
        i = 0
        while i < len(self.program_order_callstacks):
            callstack_ref = self.program_order_callstacks[i]
            if isinstance(callstack_ref, loop):
                callstack_ref.compact_callstacks()
                i += 1
                continue

            j = i+1
            while j < len(self.program_order_callstacks):
                callstack_eval = self.program_order_callstacks[j]
                if isinstance(callstack_eval, loop):
                    callstack_eval.compact_callstacks()
                    break

                if callstack_ref.same_flow(callstack_eval):
                    callstack_ref.compact_with(callstack_eval)
                    #callstack_ref.compacted_ranks.append(callstack_eval.rank)
                    del self.program_order_callstacks[j]
                else:
                    break
            i += 1

    def extracting_callstack_common_part(self):
        # Calculing the common part for subloops
        #
        for loop_obj in self.program_order_callstacks:
            if isinstance(loop_obj, loop):
                loop_obj.extracting_callstack_common_part()

        first_callstack = self.program_order_callstacks[0]
        if isinstance(first_callstack, loop):
            first_callstack = first_callstack.common_callstack

        # Getting the common callstacks
        #
        for callstack_obj in self.program_order_callstacks:
            if isinstance(callstack_obj, loop):
                callstack_obj = callstack_obj.common_callstack
            first_callstack &= callstack_obj
        self.common_callstack = first_callstack

        # Removing the common callstacks for callstacks
        #
        for callstack_i in range(len(self.program_order_callstacks)):
            if isinstance(self.program_order_callstacks[callstack_i], loop):
                self.program_order_callstacks[callstack_i]\
                        .common_callstack -= self.common_callstack
            else:
                self.program_order_callstacks[callstack_i] -= self.common_callstack

        self.loop_deph = len(self.common_callstack)-1

    def group_into_conditional_rank_blocks(self):
        # Grouping to condititional rank blocks for subloops
        #
        for loop_obj in self.program_order_callstacks:
            if isinstance(loop_obj, loop):
                loop_obj.group_into_conditional_rank_blocks()

        # Generate the first global conditional rank block
        # 
        self.conditional_rank_block = conditional_rank_block(
                self.get_all_ranks())

        # Now generate the conditional subblocks by mean of adding the 
        # subsequent callstacks/subloops
        #
        for callstack_obj in self.program_order_callstacks:
            self.conditional_rank_block.add_callstack(callstack_obj)
        self.conditional_rank_block.extracting_callstack_common_part()

    def remove_contiguous_common_callstack(self, last_common_callstack):
        
        if last_common_callstack == None:
            if type(self.conditional_rank_block.callstacks[0]) == callstack:
                last_common_callstack = self.conditional_rank_block.callstacks[0]
            else:
                last_common_callstack = self.conditional_rank_block.callstacks[0]\
                        .common_callstack
        
        for i in range(len(self.conditional_rank_block.callstacks))[1:]:
            item = self.conditional_rank_block.callstacks[i]

            if type(item) == conditional_rank_block or type(item) == loop:
                common_callstack = self.conditional_rank_block.callstacks[i]\
                        .common_callstack
                self.conditional_rank_block.callstacks[i].common_with_prev =\
                        last_common_callstack & \
                        self.conditional_rank_block.callstacks[i].common_callstack
                last_common_callstack = self.conditional_rank_block.callstacks[i]\
                        .common_callstack
                self.conditional_rank_block.callstacks[i].common_callstack -= \
                        self.conditional_rank_block.callstacks[i].common_with_prev
            else:
                common_callstack = self.conditional_rank_block.callstacks[i]
                self.conditional_rank_block.callstacks[i].common_with_prev =\
                        last_common_callstack & common_callstack

                last_common_callstack = self.conditional_rank_block.callstacks[i]
                self.conditional_rank_block.callstacks[i] -=\
                        self.conditional_rank_block.callstacks[i].common_with_prev


    def __eq__(self, other):
        if type(other) == loop:
            return self.iterations == other.iterations
        elif type(other) == callstack:
            return self.program_order_callstacks[0] == other

    def __lt__(self, other):
        if type(other) == loop:
            return self.iterations < other.iterations
        elif type(other) == callstack:
            return self.program_order_callstacks[0] < other


    def __gt__(self, other):
        if type(other) == loop:
            return self.iterations > other.iterations
        elif type(other) == callstack:
            return self.program_order_callstacks[0] > other


    def __le__(self, other):
        if type(other) == loop:
            return self.iterations <= other.iterations
        elif type(other) == callstack:
            return self.program_order_callstacks[0] <= other


    def __ge__(self, other):
        if type(other) == loop:
            return self.iterations >= other.iterations
        elif type(other) == callstack:
            return self.program_order_callstacks[0] >= other

    def __str__(self):
        val  = "> Loop iterations = {0}\n".format(self.iterations)
        val += "> Is condition = {0} ({1})\n"\
                .format(self.is_condition, self.condition_probability)
        val += "> Number of merges = {0}\n".format(self.nmerges)
        val += "> Ranks involved = {0}\n".format(self.get_all_ranks())
        val += "> Loop deph = {0}\n".format(self.loop_deph)
        val += "> Common callstack = {0}\n".format(self.common_callstack)

        val = pretty_print(val, "Loop info")

#        for callstack in self.program_order_callstacks:
#            if type(callstack) == loop:
#                val += "-> Subloop\n"
#                val += str(callstack)+"\n"
#                val += "-> End subloop\n"
#            else:
#                val += str(callstack)+"\n"

        val += str(self.conditional_rank_block)
        return val
