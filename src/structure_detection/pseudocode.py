#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import copy
from loop import loop, conditional_rank_block
from callstack import callstack
from utilities import pretty_print
from gui import *

class condition(object):
    def __init__(self, set1, set2):
        set1 = set(set1)
        set2 = set(set2)

        self.is_equal = set1 == set2
        self.is_subset = set1.issubset(set2) and not self.is_equal
        self.is_superset = set1.issuperset(set2) and not self.is_equal
        self.is_complement = len(set1.intersection(set2)) == 0

class pseudocode(object):
    def __init__(self, clusters_set, nranks, only_mpi, gui_class):
        self.gui_class = gui_class
        self.pseudo_line = gui_class.get_pseudo_line()
        self.pseudo_for = gui_class.get_pseudo_for()
        self.pseudo_for_end = gui_class.get_pseudo_for_end()
        self.pseudo_call = gui_class.get_pseudo_call()
        self.pseudo_condition = gui_class.get_pseudo_condition()

        self.lines = []
        self.all_ranks = range(nranks)
        self.only_mpi = only_mpi
        self.last_callstack = []

        # Sort the clusters by program order
        clusters_set.sort(key=lambda x: x.get_first_line(), reverse=False)

        for cluster in clusters_set:
            for loop_obj in cluster.loops:
                loop_common_cs = self.get_loop_common_calls(loop_obj, None)
                self.set_crb_common_calls(
                        loop_obj.conditional_rank_block,
                        loop_common_cs)
                self.clean_rep_callstack(loop_obj, loop_common_cs)
                self.parse_loop(loop_obj, 0)

    def set_crb_common_calls(self, crb_object, loop_cs):
        for crb in crb_object:
            cc = self.get_crb_common_calls(crb, None)
            common_cs = copy.deepcopy(cc - loop_cs)
            self.rm_crb_common_calls(crb, common_cs)
            crb.common_callstack = common_cs

    def rm_crb_common_calls(self, crb, common_cs):
        for item in crb.callstacks:
            if type(item) == loop:
                if not item.common_callstack is None:
                    for c in item.common_callstack:
                        if c in common_cs:
                            c.print_call = False
            elif type(item) == conditional_rank_block:
                self.rm_crb_common_calls(item, common_cs)
            elif type(item) == callstack:
                for c in item.calls:
                    if c in common_cs:
                        c.print_call = False

    def get_crb_common_calls(self, cond_block, last_cs):
        from_i = 0
        if last_cs is None:
            last_cs = cond_block.callstacks[0]
            if type(last_cs) == loop:
                last_cs = copy.deepcopy(last_cs.common_callstack)
            elif type(last_cs) == conditional_rank_block:
                last_cs = self.get_crb_common_calls(last_cs, None)
                last_cs = copy.deepcopy(last_cs)
            else:
                last_cs = copy.deepcopy(last_cs)

        for cs in cond_block.callstacks:
            if type(cs) == conditional_rank_block:
                last_cs &= self.get_crb_common_calls(cs, last_cs)
            elif type(cs) == loop:
                last_cs &= cs.common_callstack
            else:
                last_cs &= cs

        return last_cs
                
    def get_loop_common_calls(self, loop_obj, last_cs):
        from_i = 0
        if last_cs is None:
            last_cs = loop_obj.program_order_callstacks[0]
            if type(last_cs) == loop:
                last_cs = self.get_loop_common_calls(last_cs,None)

            from_i = 1

        last_cs = copy.deepcopy(last_cs)
        for c in last_cs.calls: 
            c.print_call = True

        for cs in loop_obj.program_order_callstacks[from_i:]:
            if type(cs) == loop:
                last_cs &= self.get_loop_common_calls(cs, None)
            else:
                last_cs &= cs
        
        loop_obj.common_callstack = last_cs
        return last_cs

    def clean_rep_callstack(self, loop_obj, last_cs):
        from_i = 0
        if last_cs is None:
            last_cs = loop_obj.program_order_callstacks[0]
            if type(last_cs) == loop:
                last_cs = last_cs.common_callstack
            from_i = 1

        for cs in loop_obj.program_order_callstacks[from_i:]:
            if type(cs) == loop: 
                self.clean_rep_callstack(cs, last_cs)
                cs = cs.common_callstack

            last_calls = last_cs.calls
            next_calls = cs.calls
            for i in range(min(len(next_calls), len(last_calls))):
                #if next_calls[i].call == last_calls[i].call:
                #    next_calls[i].print_call_name = False
                if next_calls[i] == last_calls[i]:
                    next_calls[i].print_call = False
                else:
                    break
            last_cs = cs

    def parse_loop(self, loop_obj, tabs):
        if not self.only_mpi:
            tabs += self.parse_callstack(loop_obj.common_callstack, tabs)

        loop_id = str(loop_obj.cluster_id) + ":" + str(loop_obj._id)
        self.lines.append(
                self.pseudo_for(loop_obj.iterations, loop_id, tabs))
        for crb in loop_obj.conditional_rank_block:
            self.parse_conditional_rank_block(
                    crb,
                    loop_obj.get_all_ranks(), 
                    tabs+1)
        self.lines.append(self.pseudo_for_end(loop_obj.iterations, tabs))

    def parse_callstack(self, callstack_obj, tabs):
        if callstack_obj is None:
            return 0

        calls=callstack_obj.calls
        my_tabs=0

        if not self.only_mpi:
            for call in calls:
                if not call.print_call is False:
                    if not call.my_callstack.my_loop.common_callstack\
                            is None:
                        substract = len(call.my_callstack.my_loop\
                                .common_callstack)
                    else:
                        substract = 0

                    self.lines.append(self.pseudo_call(call, 
                        tabs+my_tabs-substract))
                my_tabs += 1
        else:
            if len(calls) > 0:
                self.lines.append(self.pseudo_call(calls[-1],tabs))

        return my_tabs

    def parse_conditional_rank_block(self, 
            conditional_rank_block_obj, 
            prev_ranks,
            tabs):

        item = conditional_rank_block_obj

        # Print the common callstack
        if not self.only_mpi:
            tabs += self.parse_callstack(
                        conditional_rank_block_obj.common_callstack, 
                        tabs)

        # Print the conditional
        condition_tabs=0

        if item.ranks != self.all_ranks:
            self.lines.append(self.pseudo_condition(
                item.ranks, False, False, tabs+condition_tabs))
            condition_tabs += 1

        # Print whatever we have under the conditional
        for item in conditional_rank_block_obj.callstacks:
            if isinstance(item, loop):
                self.parse_loop(item, tabs+condition_tabs)
                prev_ranks = item.get_all_ranks()
            elif isinstance(item, conditional_rank_block):
                self.parse_conditional_rank_block(
                        item, 
                        prev_ranks, 
                        tabs+condition_tabs)
                prev_ranks = item.ranks
            else:
                tabs_c = 0
                self.parse_callstack(item, tabs+tabs_c+condition_tabs)
                prev_ranks = item.get_all_ranks()

    def show(self):
        self.gui = self.gui_class(self.lines)
        self.gui.show()
