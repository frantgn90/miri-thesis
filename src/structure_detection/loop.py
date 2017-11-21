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
        self.callstacks = []
        self.common_callstack = None

    def get_all_ranks(self):
        return self.ranks

    def agrupate(self):
        tmp_ranks = set()
        tmp = []
        result = []

        grouping_callstacks = False
        grouping_crb = False
        for cs in self.callstacks:
            if type(cs) == callstack or type(cs) == loop:
                if grouping_crb == True:
                    new_crb = conditional_rank_block(list(tmp_ranks))
                    new_crb.callstacks = tmp
                    result.append(new_crb)
                    tmp = []
                    tmp_ranks = set()
                    grouping_crb = False

                if grouping_callstacks == False:
                    tmp = [cs]
                    grouping_callstacks = True
                else:
                    tmp.append(cs)
            else:
                if grouping_callstacks == True:
                    new_crb = conditional_rank_block(self.get_all_ranks())
                    new_crb.callstacks = tmp
                    result.append(new_crb)
                    tmp = []
                    grouping_callstacks = False
                    
                if grouping_crb == False:
                    grouping_crb = True

                tmp_ranks.update(cs.get_all_ranks())
                tmp.append(cs)

                if tmp_ranks == set(self.get_all_ranks()):
                    new_crb = conditional_rank_block(list(tmp_ranks))
                    new_crb.callstacks = tmp
                    result.append(new_crb)
                    tmp = []
                    tmp_ranks = set()
                    grouping_crb = False

        if len(tmp) > 0:
            assert grouping_callstacks or grouping_crb
            if grouping_callstacks == True:
                new_crb = conditional_rank_block(self.get_all_ranks())
            elif grouping_crb == True:
                new_crb = conditional_rank_block(list(tmp_ranks))
            new_crb.callstacks = tmp
            result.append(new_crb)

        return result

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
    def __init__(self, callstacks, id):
        self._id = id
        self.cluster_id = 0

        # Maybe this loop is just an statement under a condition of 
        # other loop
        self.is_condition = False
        self.condition_probability = 0

        # Whether this loop is a hidden loop
        self.hidden_loop = False

        # Is the position where the condition of the first callstack is
        self.condition_level = None

        # This loop is made by how many merges
        self.nmerges = 1

        # Number of iterations of the loop. The original iterations
        # are needed because number of iterations will change in case
        # this loop was indeed a subloop
        if not callstacks is None:
            self.iterations = callstacks[0].repetitions[callstacks[0].rank]
        else:
            self.iterations = 0

        self.original_iterations = self.iterations

        # Sanity check 1 !!!
        #for callstack in callstacks:
        #    assert callstack.repetitions == self.iterations, \
        #            "Loop: Sanity check #1 fail"

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
        if not callstacks is None:
            self.program_order_callstacks = sorted(callstacks)
        else:
            self.program_order_callstacks = []

        self.conditional_rank_block = None
        self.already_merged = False

        logging.debug("New loop with {0} iterations."
                .format(self.iterations))

    def set_hidden_loop(self):
        assert self._id == -1
        self.hidden_loop = True

    def get_str_id(self):
        return "{0}.{1}".format(self.cluster_id, self._id)

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

    def should_own(self, cs):
        # WARNING: This function is not working well when the callstack to 
        # evaluate is be at the beggining or at the end of the loop

        first_callstack = self.get_first_callstack_po()
        last_callstack = self.get_last_callstack_po()

        aux_first = first_callstack.in_program_order
        aux_cs = cs.in_program_order
        aux_last = cs.in_program_order

        first_callstack.in_program_order = True
        cs.in_program_order = True
        last_callstack.in_program_order = True

        res = (first_callstack < cs and cs < last_callstack)

        first_callstack.in_program_order = aux_first
        cs.in_program_order = aux_cs
        last_callstack.in_program_order = aux_last

        return res

    def add_callstack(self, cs):
        self.program_order_callstacks.append(cs)
        self.program_order_callstacks.sort()

    def remove_callstack(self, cs):
        self.program_order_callstacks.remove(cs)

    def push_datacondition_callsacks(self, other):
        assert self != other

        '''
        Data condition callstacks are these callstacks that should be owned by
        one cluster that represents its loop but the use of data conditionals
        makes them behave different from the parent loop. In this case it will
        be treated as a different loop by the clustering.
        In order to avoid false loops, we can check whether a callstack should
        be owned by other loop or not by means of the code position.
        This functions is devoted to push self owned data conditional callstacks
        to the real owner.
        '''
        merged_to_other = 0
        not_merged_cs = []
        for c in self.program_order_callstacks:
            '''
            Because at this point no merge has to be done yet.
            Now c could be a loop because hiden super-loop analysis
            is done, so in this case, self is a hiden super-loop
            '''
            assert not type(c) == loop

            if other.should_own(c):
                other.add_callstack(c)
                merged_to_other += 1
            else:
                not_merged_cs.append(c)
        self.program_order_callstacks = not_merged_cs

        if merged_to_other == 0:
            return 0 # Not pushed
        elif len(self.program_order_callstacks) == 0:
            return 1 # Completelly pushed
        else:
            return 2 # Partially pushed

    def merge_with_subloop(self, other):
        # This sitation happens when hidden super-loop is detected
        # on subloop cluster
        if other.iterations == self.iterations:
            merged_subloop = self.program_order_callstacks + \
                    other.program_order_callstacks
        else:
            other.iterations /= self.iterations
            merged_subloop = self.program_order_callstacks + [other]

        def __sort_loops_and_cs(a, b):
            result = False

            if type(a) == loop:
                a_to_compare = a.get_first_callstack()
            else:
                a_to_compare = a

            if type(b) == loop:
                b_to_compare = b.get_first_callstack()
            else:
                b_to_compare = b

            if a_to_compare < b_to_compare:
                result = -1
            else:
                result = 1

            return result

        merged_subloop.sort(__sort_loops_and_cs)
        self.program_order_callstacks = merged_subloop

        for toc in self.program_order_callstacks:
            if type(toc) == callstack:
                common_callstack = toc

        # TODO
        # This is assuming all loops will have at least one callstack
        # but now we have synthetic superloops that just have subloops
        # think about it

        #i=0
        #common_callstack = self.program_order_callstacks[i]
        #while isinstance(common_callstack, loop):
        #    i += 1
        #    common_callstack = self.program_order_callstacks[i]

    def get_first_line(self):
        if type(self.program_order_callstacks[0]) == loop:
            return self.program_order_callstacks[0].get_first_line()
        else:
            return self.program_order_callstacks[0].calls[0].line

    def get_first_callstack(self):
        if type(self.program_order_callstacks[0]) == loop:
            return self.program_order_callstacks[0].get_first_callstack()
        else:
            return self.program_order_callstacks[0]

    def get_last_callstack(self):
        if type(self.program_order_callstacks[-1]) == loop:
            return self.program_order_callstacks[-1].get_last_callstack()
        else:
            return self.program_order_callstacks[-1]

    def get_first_callstack_po(self):
        import copy
        prev_order = []
        for cs in self.program_order_callstacks:
            prev_order.append(cs.in_program_order)

        po_callstack = copy.copy(self.program_order_callstacks)
        for cs in po_callstack:
            cs.in_program_order = True
        po_callstack.sort()

        if type(po_callstack[0]) == loop:
            res = po_callstack[0].get_first_callstack_po()
        else:
            res = po_callstack[0]

        nrange = range(len(self.program_order_callstacks))
        for cs in zip(self.program_order_callstacks, nrange):
            cs[0].in_program_order = prev_order[cs[1]]

        return res

    def get_last_callstack_po(self):
        import copy
        prev_order = []
        for cs in self.program_order_callstacks:
            prev_order.append(cs.in_program_order)

        po_callstack = copy.copy(self.program_order_callstacks)
        for cs in po_callstack:
            cs.in_program_order = True
        po_callstack.sort()

        if type(po_callstack[-1]) == loop:
            res = po_callstack[-1].get_last_callstack_po()
        else:
            res = po_callstack[-1]

        nrange = range(len(self.program_order_callstacks))
        for cs in zip(self.program_order_callstacks, nrange):
            cs[0].in_program_order = prev_order[cs[1]]

        return res

    def get_first_callstack_instants(self):
        instants = None
        if self.hidden_loop:
            first_loop = None
            for l in self.program_order_callstacks:
                if type(l) == loop:
                    first_loop = l
                    break
            instants = first_loop.get_first_callstack_instants()
            instants = instants[::self.iterations]
        else:
            first_callstack = None
            for c in self.program_order_callstacks:
                if type(c) == callstack:
                    first_callstack = c
                    break
            instants = first_callstack.instants

        assert not instants is None
        return instants

        #if type(self.program_order_callstacks[0]) == loop:
        #    return self.program_order_callstacks[0]\
        #        .get_first_callstack_instants()
        #else:
        #    return self.program_order_callstacks[0].instants

    def is_subloop(self, other):
        its_bounds = None
        sub_times = None

        if self.iterations == other.iterations:
            logging.warning("Think little bit more about it!!")
            return True

        # Could be the situation where self of other just have subloops
        # w/o callstacks when temp_matrix detect a hidden superloop
        #for cs in self.program_order_callstacks:
        #    if type(cs) == callstack:
        #        its_bounds = cs.instants
        #    elif type(cs) == loop:
        #        its_bounds = cs.get_first_callstack().instants
        #
        #for cs in other.program_order_callstacks:
        #    if type(cs) == callstack:
        #        sub_times = cs.instants
        #    elif type(cs) == loop:
        #        sub_times = cs.get_first_callstack().instants

        its_bounds = self.get_first_callstack_instants()
        sub_times = other.get_first_callstack_instants()

        assert not its_bounds is None and not sub_times is None

        its_bounds = filter(lambda x: x != 0, its_bounds)
        sub_times = filter(lambda x: x != 0, sub_times)

        if sub_times[0] < its_bounds[0]:
            its_bounds = [0] + its_bounds

        last_j = 0
        for i in range(len(its_bounds)-1):
            lower_bound = int(its_bounds[i])
            upper_bound = int(its_bounds[i+1])

            inner_its = 0
            for j in range(last_j, len(sub_times)):
                inner_time = int(sub_times[j])

                if inner_time > lower_bound and inner_time < upper_bound:
                    inner_its += 1
                else:
                    last_j = j
                    break
            if inner_its == 0:
                return False

        return True


        #last_j = 0
        #is_subloop = False
        #
        #for i in range(len(its_bounds))[0::2]:
        #    if i+1 >= len(its_bounds): break
        #    lower_bound = its_bounds[i]
        #    upper_bound = its_bounds[i+1]
        #
        #    for j in range(last_j, len(sub_times)):
        #        if sub_times[j] >= lower_bound and sub_times[j] <= upper_bound:
        #            is_subloop = True
        #            break
        #
        #return is_subloop;

    def compact_callstacks(self, callstacks_pool):
        i = 0
        cs_to_remove = []
    
        while i < len(self.program_order_callstacks):
            if i in cs_to_remove: i+=1; continue
            callstack_ref = self.program_order_callstacks[i]
            if isinstance(callstack_ref, loop):
                callstack_ref.compact_callstacks(callstacks_pool)
                i += 1; continue

            j = i+1
            while j < len(self.program_order_callstacks):
                if j in cs_to_remove: j+=1; continue
                callstack_eval = self.program_order_callstacks[j]
                if isinstance(callstack_eval, loop):
                    callstack_eval.compact_callstacks(callstacks_pool)
                    break

                if callstack_ref.same_flow(callstack_eval):
                    callstack_ref.compact_with(callstack_eval)
                    #callstack_ref.compacted_ranks.append(callstack_eval.rank)
                    callstacks_pool.remove(callstack_eval)
                    #del self.program_order_callstacks[j]
                    cs_to_remove.append(j)
                    j+=1
                else:
                    #break
                    j+=1; continue
            i += 1

        aux = []
        for i in range(len(self.program_order_callstacks)):
            if not i in cs_to_remove:
                aux.append(self.program_order_callstacks[i])
        self.program_order_callstacks = aux

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
        for loop_obj in self.program_order_callstacks:
            if isinstance(loop_obj, loop):
                loop_obj.group_into_conditional_rank_blocks()

        # Generate the first global conditional rank block
        crb = conditional_rank_block(self.get_all_ranks())

        # Now generate the conditional subblocks by mean of adding the 
        # subsequent callstacks/subloops
        for callstack_obj in self.program_order_callstacks:
            crb.add_callstack(callstack_obj)

        self.conditional_rank_block = crb.agrupate()
        #self.conditional_rank_block.extracting_callstack_common_part()

    def group_into_conditional_data_blocks(self):
        pass

    def remove_contiguous_common_callstack(self, last_common_callstack):
        
        if last_common_callstack is None:
            if type(self.conditional_rank_block.callstacks[0]) == callstack:
                last_common_callstack = \
                    self.conditional_rank_block.callstacks[0]
            else:
                last_common_callstack = \
                    self.conditional_rank_block.callstacks[0].common_callstack
        
        for i in range(len(self.conditional_rank_block.callstacks))[1:]:
            item = self.conditional_rank_block.callstacks[i]

            if type(item) == conditional_rank_block or type(item) == loop:
                if type(item) == loop:
                    item.remove_contiguous_common_callstack(last_common_callstack)
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

    def get_iteration_times():
        first_callstack = self.get_first_callstack()
        last_callstack = self.get_last_callstack()

        assert len(first_callstack.instants) == len(last_callstacks.instants)
        return zip(first_callstack.instants, last_callstack.instants)

    def callstack_set_owner_loop(self):
        for cs in self.program_order_callstacks:
            if type(cs) == loop:
                cs.callstack_set_owner_loop()
            else:
                cs.my_loop = self               

    def __len__(self):
        return len(self.program_order_callstacks)

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

        for callstack in self.program_order_callstacks:
            if type(callstack) == loop:
                val += "-> Subloop\n"
                val += str(callstack)+"\n"
                val += "-> End subloop\n"
            else:
                val += str(callstack)+"\n"

        return val
