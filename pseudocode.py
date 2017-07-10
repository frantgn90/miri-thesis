#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from loop import loop
from callstack import callstack

class pseudo_line(object):
    def __init__(self, deph):
        self.deph = deph

    def get_tabs(self):
        return ":  "*self.deph

class pseudo_for(pseudo_line):
    def __init__(self, iterations, deph):
        pseudo_line.__init__(self, deph)
        self.iterations = iterations

    def __str__(self):
        res = self.get_tabs() + "FOR 1 TO {0}".format(self.iterations)
        return res

class pseudo_for_end(pseudo_line):
    def __init__(self, iterations, deph):
        pseudo_line.__init__(self, deph)
        self.iterations = iterations

    def __str__(self):
        res = self.get_tabs() + "END LOOP"
        return res

class pseudo_call(pseudo_line):
    def __init__(self, call, deph):
        pseudo_line.__init__(self, deph)
        self.call = call
        self.deph = deph

    def __str__(self):
        res = self.get_tabs() + "{0}()".format(self.call.call)
        return  res

class pseudo_condition(pseudo_line):
    def __init__(self, ranks, el, eli, deph):
        pseudo_line.__init__(self, deph)
        self.ranks = ranks
        self.el = el
        self.eli = eli

    def __str__(self):
        if self.el:
            res = self.get_tabs() + "ELSE".format(self.ranks)
        elif self.eli:
            res = self.get_tabs() + "ELSE IF RANK in {0}".format(self.ranks)
        else:
            res = self.get_tabs() + "IF RANK IN {0}".format(self.ranks)
        return res

class condition(object):
    def __init__(self, set1, set2):
        set1 = set(set1)
        set2 = set(set2)

        self.is_equal = set1 == set2
        self.is_subset = set1.issubset(set2) and not self.is_equal
        self.is_superset = set1.issuperset(set2) and not self.is_equal
        self.is_complement = len(set1.intersection(set2)) == 0
 

class pseudocode(object):
    def __init__(self, clusters_set):
        self.lines = []
        for cluster in clusters_set:
            for loop_obj in cluster.loops:
                self.parse_loop(loop_obj, 0, 0)

        print
        for line in self.lines:
            print str(line)
        print

    def parse_loop(self, loop_obj, stack_deph, tabs):
        # Callstack to loop
        #
        for cs in loop_obj.program_order_callstacks:
            if isinstance(cs, callstack):
                first_callstack = cs
        assert first_callstack
        for call_obj in first_callstack.calls[stack_deph:loop_obj.loop_deph+1]:
            self.lines.append(pseudo_call(call_obj, tabs))
            tabs += 1

        # Loop body
        #
        #all_ranks = [0,1,2,3,4,5,6,7]
        all_ranks = [0,1,2,3]
        prev_ranks = all_ranks
        nested_conditions = 0
        self.lines.append(pseudo_for(loop_obj.iterations, tabs))
        for callstack_obj in loop_obj.program_order_callstacks:
            condition_obj = condition(callstack_obj.get_all_ranks(), prev_ranks)

            if callstack_obj.get_all_ranks() == all_ranks:
                nested_conditions = 0
            elif condition_obj.is_subset:
                self.lines.append(
                        pseudo_condition(
                            callstack_obj.get_all_ranks(), False, False,
                            tabs+nested_conditions+1))
                nested_conditions += 1
            elif condition_obj.is_complement:
                nested_conditions -= 1
                if set(prev_ranks).union(set(callstack_obj.get_all_ranks()))\
                        == set(all_ranks):
                            el = True
                            eli = False
                else:
                    el = False
                    eli = True
                self.lines.append(
                        pseudo_condition(
                            callstack_obj.get_all_ranks(), el, eli,
                            tabs+nested_conditions+1))
                nested_conditions += 1
            elif condition_obj.is_equal:
                pass
            elif condition_obj.is_superset:
                nested_conditions -= 1
                self.lines.append(
                        pseudo_condition(
                            callstack_obj.get_all_ranks(), False, False,
                            tabs+nested_conditions+1))
                nested_conditions += 1
            prev_ranks = callstack_obj.get_all_ranks()

            if isinstance(callstack_obj, loop):
                self.parse_loop(callstack_obj, loop_obj.loop_deph+1, tabs+nested_conditions+1)
            else:
                call_tabs = tabs + nested_conditions + 1
                self.parse_callstack(callstack_obj, loop_obj.loop_deph+1, loop_obj, call_tabs)


        self.lines.append(pseudo_for_end(loop_obj.iterations, tabs))

    def parse_callstack(self, callstack_obj, block_deph, loop_obj, tabs):
        calls = callstack_obj.calls[block_deph:]
        call_deph = block_deph
        for call in calls:
            self.lines.append(pseudo_call(call, tabs))
            tabs += 1
            call_deph += 1


    def __generate_html(self):
        pass

    def show(self):
        pass


