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
    def __init__(self, clusters_set, nranks, only_mpi, gui_class, 
            show_burst_info):
        self.gui_class = gui_class
        self.pseudo_line = gui_class.get_pseudo_line()
        self.pseudo_for = gui_class.get_pseudo_for()
        self.pseudo_for_end = gui_class.get_pseudo_for_end()
        self.pseudo_call = gui_class.get_pseudo_call()
        self.pseudo_condition = gui_class.get_pseudo_condition()
        self.pseudo_computation = gui_class.get_pseudo_computation()

        self.lines = []
        self.all_ranks = set(range(nranks))
        self.only_mpi = only_mpi
        self.show_burst_info = show_burst_info

        # Sort the clusters by program order
        clusters_set.sort(key=lambda x: x.get_first_line(), reverse=False)

        for cluster in clusters_set:
            for loop_obj in cluster.loops:
                loop_obj.extract_common_callstack_r()
                loop_obj.hide_contiguous_callstacks()
                self.parse_loop(loop_obj, 0)


        self.gui = self.gui_class(self.lines)

    def parse_loop(self, loop_obj, tabs):
        if not self.only_mpi:
            tabs += self.parse_callstack(loop_obj.common_callstack, tabs)

        loop_id = str(loop_obj.cluster_id) + ":" + str(loop_obj._id)
        self.lines.append(
                self.pseudo_for(loop_obj.iterations, loop_id, tabs))
        #for crb in loop_obj.conditional_rank_block:
        for crb in loop_obj.callstack_list:
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
                    if call.mpi_call and self.show_burst_info:
                        self.lines.append(
                                self.pseudo_computation(call,tabs+my_tabs))
                    self.lines.append(self.pseudo_call(call, tabs+my_tabs))
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

        if item.get_all_ranks() != self.all_ranks:
            self.lines.append(self.pseudo_condition(
                item.ranks, False, False, tabs+condition_tabs))
            condition_tabs += 1

        # Print whatever we have under the conditional
        for item in conditional_rank_block_obj.callstack_list:
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
        self.gui.show()
