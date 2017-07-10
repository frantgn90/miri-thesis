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

class loop (object):
    def __init__(self, callstacks):
        # Maybe this loop is just an statement under a condition of 
        # other loop
        #
        self.is_condition = False
        self.condition_probability = 0

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
        for callstack in callstacks:
            assert callstack.repetitions == self.iterations, \
                    "Loop: Sanity check #1 fail"

        # We have a chain of calls, this variable indicates where
        # in this chain the loop represented by this object is. The way
        # to calculate it is to get just the common part of all the
        # chains
        #
        common_callstack = callstacks[0]
        for callstack in callstacks:
            common_callstack &= callstack
        self.loop_deph = len(common_callstack.calls)
        self.common_calls = common_callstack.calls

        # Until now, the order of the callstacks were not important
        # but now it is, so lets sort it. The order should be the
        # program order so the line is the parameter to take into account
        self.program_order_callstacks = sorted(callstacks)

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

        merged_callstacks = other.program_order_callstacks + self.program_order_callstacks
        self.program_order_callstacks = sorted(merged_callstacks)

        self.nmerges += 1

        common_callstack = self.program_order_callstacks[0]
        for callstack in self.program_order_callstacks:
            common_callstack &= callstack
        self.loop_deph = len(common_callstack.calls)
        self.common_calls = common_callstack.calls

    def merge_with_subloop(self, other):
        # The difference with the previous merge is that now 'other' is a subloop
        # of ourselfs. So new comparative functions have to be added to this class

        merged_subloop = self.program_order_callstacks + other
        self.program_order_callstacks = sorted(merged_subloop)

        i=0
        common_callstack = self.program_order_callstacks[i]
        while isinstance(common_callstack, loop):
            i += 1
            common_callstack = self.program_order_callstacks[i]

        for callstack in self.program_order_callstacks:
            if isinstance(callstack, loop):
                for sl_callstack in callstack.program_order_callstacks:
                    if isinstance(sl_callstack, loop):
                        continue
                    else:
                        common_callstack &= sl_callstack
            else:
                common_callstack &= callstack
        self.loop_deph = len(common_callstack.calls)
        self.common_calls = common_callstack.calls


    def is_subloop(self, other):
        its_bounds = self.program_order_callstacks[0].instants
        sub_times  = other.program_order_callstacks[0].instants

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
                    callstack_ref.compacted_ranks.append(callstack_eval.rank)
                    del self.program_order_callstacks[j]
                else:
                    break
            i += 1

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

        val = pretty_print(val, "Loop info")

        for callstack in self.program_order_callstacks:
            if type(callstack) == loop:
                val += "-> Subloop\n"
                val += str(callstack)+"\n"
                val += "-> End subloop\n"
            else:
                val += str(callstack)+"\n"
        return val
