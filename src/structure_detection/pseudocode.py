#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from loop import loop, conditional_rank_block
from callstack import callstack
from utilities import pretty_print
from gui import *

class pseudo_line(object):
    def __init__(self, deph):
        self.deph = deph
        self.first_col = "--"
        self.second_col = "--"
        self.third_col = "--"
        self.metric = "metric..."
        self.metric_2 = ""

    def get_tabs(self):
        return ":  "*self.deph

    def __str__(self):
        res = "{0:10.10} {1:>5} {2:30} {3:10} {4}".format(
                self.first_col,
                self.second_col, 
                (self.get_tabs() + self.third_col), 
                self.metric,
                self.metric_2)
        return res

class pseudo_for(pseudo_line):
    def __init__(self, iterations, deph):
        pseudo_line.__init__(self, deph)
        self.iterations = iterations
        self.first_col = ""
        self.second_col = " "
        self.third_col = "FOR 1 TO {0}".format(self.iterations)
        self.metric = ""

class pseudo_for_end(pseudo_line):
    def __init__(self, iterations, deph):
        pseudo_line.__init__(self, deph)
        self.iterations = iterations
        self.first_col = ""
        self.second_col = " "
        self.third_col = "END LOOP"
        self.metric = ""

class pseudo_call(pseudo_line):
    def __init__(self, call, deph):
        pseudo_line.__init__(self, deph)
        self.call = call
        self.first_col = self.call.call_file
        if self.call.mpi_call:
            self.second_col = "UNK"
            self.metric = str(
                    self.call.my_callstack.metrics["mpi_duration_mean"])
            self.metric_2 = str(
                    self.call.my_callstack.metrics["mpi_duration_stdev"])

        else:
            self.second_col = str(self.call.line)
            self.metric = ""
        self.third_col = "{0}()".format(self.call.call)

class pseudo_condition(pseudo_line):
    def __init__(self, ranks, el, eli, deph):
        pseudo_line.__init__(self, deph)
        self.ranks = ranks
        self.el = el
        self.eli = eli

        self.first_col = ""
        self.second_col = " "
        if self.el:
            self.third_col = "ELSE"
        elif self.eli:
            self.third_col = "ELSE IF RANK in {0}".format(self.ranks)
        else:
            self.third_col = "IF RANK IN {0}".format(self.ranks)
        self.metric = ""


class condition(object):
    def __init__(self, set1, set2):
        set1 = set(set1)
        set2 = set(set2)

        self.is_equal = set1 == set2
        self.is_subset = set1.issubset(set2) and not self.is_equal
        self.is_superset = set1.issuperset(set2) and not self.is_equal
        self.is_complement = len(set1.intersection(set2)) == 0

class pseudocode(object):
    def __init__(self, clusters_set, nranks, only_mpi):
        self.lines = []
        self.all_ranks = range(nranks)
        self.only_mpi = only_mpi

        # Sort the clusters by program order
        #
        clusters_set.sort(key=lambda x: x.get_first_line(), reverse=False)
        #clusters_set.reverse()

        for cluster in clusters_set:
            for loop_obj in cluster.loops:
                self.parse_loop(loop_obj, 0)

    def parse_loop(self, loop_obj, tabs):
        # Callstack to loop
        #
        tabs += self.parse_callstack(loop_obj.common_callstack, tabs)

        # Loop description
        #
        self.lines.append(pseudo_for(loop_obj.iterations, tabs))
        self.parse_conditional_rank_block(
                loop_obj.conditional_rank_block,
                loop_obj.get_all_ranks(), 
                tabs+1)
        self.lines.append(pseudo_for_end(loop_obj.iterations, tabs))

    def parse_callstack(self, callstack_obj, tabs):
        calls = callstack_obj.calls
        my_tabs=0

        if not self.only_mpi:
            for call in calls:
                self.lines.append(pseudo_call(call, tabs+my_tabs))
                my_tabs += 1
        else:
            if len(calls) > 0:
                self.lines.append(pseudo_call(calls[-1],tabs))
        return my_tabs

    def parse_conditional_rank_block(self, 
            conditional_rank_block_obj, 
            prev_ranks,
            tabs):
        condition_tabs=0
        my_ranks = set(conditional_rank_block_obj.ranks)
        
        condition_obj = condition(my_ranks, prev_ranks)

        item = conditional_rank_block_obj
        if item.ranks == prev_ranks:
            condition_tabs = 0
        elif condition_obj.is_subset:
            self.lines.append(pseudo_condition(
                item.ranks, False, False, tabs+condition_tabs))
            condition_tabs += 1
        elif condition_obj.is_complement:
            if set(prev_ranks).union(set(item.ranks)) == set(self.all_ranks):
                #el = True; eli = False
                el = False; eli = True
            else:
                el = False; eli = True

            self.lines.append(pseudo_condition(item.ranks, 
                el, eli,tabs+condition_tabs))
            condition_tabs += 1
        elif condition_obj.is_equal:
            pass
        elif condition_obj.is_superset:
            self.lines.append(pseudo_condition(item.ranks, False, False,
                tabs+condition_tabs))
            condition_tabs += 1

        tabs += self.parse_callstack(
                conditional_rank_block_obj.common_callstack, 
                tabs+1)

        
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
                self.parse_callstack(item, tabs+condition_tabs)
                prev_ranks = item.get_all_ranks()


    def show_console(self):
        self.gui = console_gui(self.lines)
        self.gui.show()

    def show_html(self):
        pass

