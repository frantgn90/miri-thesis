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

class callstack_ordered_list(object):
    def __init__(self, callstacks):
        self.callstack_ranks = set()
        self.common_callstack = None
        if callstack is None:
            self.callstack_list = []
        else:
            self.callstack_list = callstacks

    def add_callstack(self, callstack):
        assert not callstack in self.callstack_list

        self.callstack_list.append(callstack)
        self.callstack_list.sort()

    def remove_callstack(self, callstack):
        res = False
        if callstack in self.callstack_list:
            i = self.callstack_list.index(callstack)
            del self.callstack_list[i]
            res = True
        else:
            for cs in self.callstack_list:
                if isinstance(cs, callstack_ordered_list):
                    done = cs.remove_callstack(callstack)
                    if done: res = True

        self.callstack_ranks = set([x.get_all_ranks() 
            for x in self.callstack_list])
        return res

    def get_all_ranks(self):
        for cs in self.callstack_list:
            self.callstack_ranks.update(cs.get_all_ranks())
        return self.callstack_ranks

    def get_common_callstack(self):
        """ could be implemented as a parallel reduce """
        common_callstack = self.callstack_list[0]
        if isinstance(common_callstack, callstack_ordered_list):
            common_callstack = common_callstack.common_callstack

        for item in self.callstack_list:
            if isinstance(item, callstack_ordered_list):
                assert not item.common_callstack is None
                common_callstack &= item.common_callstack
            else:
                common_callstack &= item

        return common_callstack

    def remove_calls_from_callstacks(self, callstack):
        nitems = len(self.callstack_list)
        for i,item in zip(range(nitems),self.callstack_list):
            if isinstance(item, callstack_ordered_list):
                item.common_callstack -= callstack
                item.remove_calls_from_callstacks(callstack)
            else:
                self.callstack_list[i] = item - callstack

    def set_common_callstack(self, callstack):
        """ could be done completely in parallel """
        assert self.common_callstack is None
        self.common_callstack = callstack
        self.remove_calls_from_callstacks(self.common_callstack)

    def extract_common_callstack_r(self):
        """ extract common callstack recursivelly """
        for item in self.callstack_list:
            if isinstance(item, callstack_ordered_list):
                item.extract_common_callstack_r()

        common_callstack = self.get_common_callstack()
        self.set_common_callstack(common_callstack)

    def get_flat_callstack_list(self):
        result = []
        self.get_flat_callstack_list_r(result)
        return result

    def get_flat_callstack_list_r(self, result):
        for item in self.callstack_list:
            if isinstance(item, callstack_ordered_list):
                item.get_flat_callstack_list_r(result)
            else:
                result.append(item)

    def hide_contiguous_callstacks(self):
        callstacks = self.get_flat_callstack_list()
        last_cs = callstacks[0]

        for cs in callstacks[1:]:
            last_calls = last_cs.calls
            next_calls = cs.calls

            for i in range(min(len(next_calls), len(last_calls))):
                if next_calls[i] == last_calls[i]:
                    next_calls[i].print_call = False
                else:
                    break
            last_cs = cs

        self.hide_continguous_common_callstacks()

    def hide_continguous_common_callstacks(self):
        last_cs = self.common_callstack

        for cs in self.callstack_list:
            if isinstance(cs, callstack_ordered_list):
                next_cs = cs.common_callstack

                last_calls = last_cs.calls
                next_calls = next_cs.calls

                for i in range(min(len(next_calls), len(last_calls))):
                    if next_calls[i] == last_calls[i]:
                        next_calls[i].print_call = False
                    else:
                        break
                last_cs = cs.common_callstack
                cs.hide_continguous_common_callstacks()


    def get_first_callstack(self):
        return self.get_callstack_from_pos(0)

    def get_last_callstack(self):
        return self.get_callstack_from_pos(-1)

    def get_callstack_from_pos(self, pos):
        callstack_flat_list = self.get_flat_callstack_list()
        return callstack_flat_list[pos]
        #item = self.callstack_list[pos]
        #if isinstance(item, callstack_ordered_list):
        #    # WARNING: Could not work in all cases
        #    return item.get_callstack_from_pos(pos)
        #return item

class conditional_rank_block(callstack_ordered_list):
    def __init__(self, ranks):
        super(conditional_rank_block, self)\
                .__init__([])
        self.ranks = ranks

    def get_all_ranks(self):
        return set(self.ranks)

    def agrupate(self):
        tmp_ranks = set()
        tmp = []
        result = []

        grouping_callstacks = False
        grouping_crb = False
        for cs in self.callstack_list:
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
                    new_crb.callstack_list = tmp
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
            new_crb.callstack_list = tmp
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
            self.callstack_list.append(callstack_or_loop)
            return
        elif is_superset:
            if len(self.callstack_list) > 0:
                if isinstance(self.callstack_list[-1], conditional_rank_block):
                    last_cond_block = self.callstack_list[-1]

                    # Let's see if we have a subsubblock or just a subblock
                    #
                    set1 = set(last_cond_block.ranks)
                    set2 = set(callstack_or_loop.get_all_ranks())
                    is_equal = set1 == set2
                    is_subset = set1.issubset(set2) and not is_equal
                    is_superset = set1.issuperset(set2) and not is_equal
                    is_complement = len(set1.intersection(set2)) == 0

                    if is_equal or is_superset:
                        self.callstack_list[-1].add_callstack(callstack_or_loop)
                    else:
                        new_cond_block = conditional_rank_block(
                            callstack_or_loop.get_all_ranks())
                        new_cond_block.add_callstack(callstack_or_loop)
                        self.callstack_list.append(new_cond_block)
                else:
                    new_cond_block = conditional_rank_block(
                        callstack_or_loop.get_all_ranks())
                    new_cond_block.add_callstack(callstack_or_loop)
                    self.callstack_list.append(new_cond_block)
            else:
                new_cond_block = conditional_rank_block(
                        callstack_or_loop.get_all_ranks())
                new_cond_block.add_callstack(callstack_or_loop)
                self.callstack_list.append(new_cond_block)
            return
        assert False

    def callstack_set_owner_loop(self, owner):
        for item in self.callstack_list:
            if isinstance(item, loop):
                item.callstack_set_owner_loop()
            elif isinstance(item, conditional_rank_block):
                item.callstack_set_owner_loop(owner)
            else:
                item.my_loop = owner

    def __str__(self):
        res  = "Ranks: {0}\n".format(self.ranks)
        res += "Common: {0}\n".format(self.common_callstack)
        if len(self.callstack_list) > 0:
            res += "***** [CONTENT] *****\n"
            for callstack_obj in self.callstack_list:
                if isinstance(callstack_obj, loop):
                    res += "LOOP Ranks:{0} Ncallstacks:{1}\n"\
                            .format(callstack_obj.get_all_ranks(), 
                                    len(callstack_obj.callstack_list))
                elif isinstance(callstack_obj, conditional_rank_block):
                    res += "--- Subblock ---\n"
                    res += str(callstack_obj)
                    res += "--- End subblock ---\n"
                else:
                    res += str(callstack_obj) + "\n"
            res += "*********************\n"
        return res

class loop (callstack_ordered_list):
    def __init__(self, callstacks, id):
        super(loop, self).__init__(callstacks)

        self._id = id
        self.cluster_id = 0

        # Whether this loop is a hidden loop
        self.hidden_loop = False

        # This loop is made by how many merges
        self.nmerges = 1

        # Number of iterations of the loop. The original iterations
        # are needed because number of iterations will change in case
        # this loop was indeed a subloop
        if len(callstacks) > 0:
            self.iterations = callstacks[0].repetitions[callstacks[0].rank]
        else:
            self.iterations = 0
        self.original_iterations = self.iterations
        #self.conditional_rank_block = None
        self.already_merged = False

        logging.debug("New loop with {0} iterations."
                .format(self.iterations))

    def set_hidden_loop(self):
        assert self._id == -1
        self.hidden_loop = True

    def get_str_id(self):
        return "{0}.{1}".format(self.cluster_id, self._id)

    def merge(self, other):
        assert type(other) == loop
        assert other.nmerges == 1

        merged_callstacks = other.callstack_list\
                + self.callstack_list
        self.callstack_list = sorted(merged_callstacks)
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
        for c in self.callstack_list:
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
        self.callstack_list = not_merged_cs

        if merged_to_other == 0:
            return 0 # Not pushed
        elif len(self.callstack_list) == 0:
            return 1 # Completelly pushed
        else:
            return 2 # Partially pushed

    def merge_with_subloop(self, other):
        # This sitation happens when hidden super-loop is detected
        # on subloop cluster
        if other.iterations == self.iterations:
            merged_subloop = self.callstack_list + \
                    other.callstack_list
        else:
            other.iterations /= self.iterations
            merged_subloop = self.callstack_list + [other]

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
        self.callstack_list = merged_subloop

        for toc in self.callstack_list:
            if type(toc) == callstack:
                common_callstack = toc

        # TODO
        # This is assuming all loops will have at least one callstack
        # but now we have synthetic superloops that just have subloops
        # think about it

        #i=0
        #common_callstack = self.callstack_list[i]
        #while isinstance(common_callstack, loop):
        #    i += 1
        #    common_callstack = self.callstack_list[i]

    def get_first_line(self):
        cs = self.get_first_callstack_po()
        return cs.calls[0].line 

        #if type(self.callstack_list[0]) == loop:
        #    return self.callstack_list[0].get_first_line()
        #else:
        #    return self.callstack_list[0].calls[0].line

    def get_first_callstack_po(self):
        callstacks_copy = copy.deepcopy(self.get_flat_callstack_list())

        for cs in callstacks_copy:
            cs.in_program_order = True

        callstacks_copy.sort()
        return callstacks_copy[0]

    def get_last_callstack_po(self):
        callstacks_copy = copy.deepcopy(self.get_flat_callstack_list())

        for cs in callstacks_copy:
            cs.in_program_order = True

        callstacks_copy.sort()
        return callstacks_copy[-1]

    def get_first_callstack_instants(self):
        instants = None
        if self.hidden_loop:
            first_loop = None
            for l in self.callstack_list:
                if type(l) == loop:
                    first_loop = l
                    break
            instants = first_loop.get_first_callstack_instants()
            instants = instants[::self.iterations]
        else:
            first_callstack = None
            for c in self.callstack_list:
                if type(c) == callstack:
                    first_callstack = c
                    break
            instants = first_callstack.instants

        assert not instants is None
        return instants

        #if type(self.callstack_list[0]) == loop:
        #    return self.callstack_list[0]\
        #        .get_first_callstack_instants()
        #else:
        #    return self.callstack_list[0].instants

    def is_subloop(self, other):
        its_bounds = None
        sub_times = None

        if self.iterations == other.iterations:
            logging.warning("Think little bit more about it!!")
            return True

        # Could be the situation where self of other just have subloops
        # w/o callstacks when temp_matrix detect a hidden superloop
        #for cs in self.callstack_list:
        #    if type(cs) == callstack:
        #        its_bounds = cs.instants
        #    elif type(cs) == loop:
        #        its_bounds = cs.get_first_callstack().instants
        #
        #for cs in other.callstack_list:
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
    
        while i < len(self.callstack_list):
            if i in cs_to_remove: i+=1; continue
            callstack_ref = self.callstack_list[i]
            if isinstance(callstack_ref, loop):
                callstack_ref.compact_callstacks(callstacks_pool)
                i += 1; continue

            j = i+1
            while j < len(self.callstack_list):
                if j in cs_to_remove: j+=1; continue
                callstack_eval = self.callstack_list[j]
                if isinstance(callstack_eval, loop):
                    callstack_eval.compact_callstacks(callstacks_pool)
                    break

                if callstack_ref.same_flow(callstack_eval):
                    callstack_ref.compact_with(callstack_eval)
                    #callstack_ref.compacted_ranks.append(callstack_eval.rank)
                    callstacks_pool.remove(callstack_eval)
                    #del self.callstack_list[j]
                    cs_to_remove.append(j)
                    j+=1
                else:
                    #break
                    j+=1; continue
            i += 1

        aux = []
        for i in range(len(self.callstack_list)):
            if not i in cs_to_remove:
                aux.append(self.callstack_list[i])
        self.callstack_list = aux

    def group_into_conditional_rank_blocks(self):
        # Grouping to condititional rank blocks for subloops
        for loop_obj in self.callstack_list:
            if isinstance(loop_obj, loop):
                loop_obj.group_into_conditional_rank_blocks()

        #import pdb; pdb.set_trace()
        # Generate the first global conditional rank block
        crb = conditional_rank_block(self.get_all_ranks())

        # Now generate the conditional subblocks by mean of adding the 
        # subsequent callstacks/subloops
        for callstack_obj in self.callstack_list:
            crb.add_callstack(callstack_obj)

        #self.callstack_list = crb.agrupate()
        self.callstack_list = [crb]
        #self.conditional_rank_block = crb.agrupate()

    def get_iteration_times(self):
        first_callstack = self.get_first_callstack()
        last_callstack = self.get_last_callstack()

        
        fc_times = first_callstack.get_instants()
        lc_times = last_callstack.get_end_instants()

        min_its = min(len(fc_times), len(lc_times))

        if len(fc_times) > min_its:
            part = int(len(fc_times)/min_its)
            fc_times = fc_times[::part]

        if len(lc_times) > min_its:
            part = int(len(lc_times)/min_its)
            lc_times = lc_times[::part]

        assert len(fc_times) == len(lc_times)
        return zip(fc_times, lc_times)

    def get_iteration(self, nit):
        its = self.get_iteration_times()

        if nit >= len(its) or nit < 0:
            return None
        return its[nit]

    def callstack_set_owner_loop(self):
        #callstacks = self.get_flat_callstack_list()
        #for cs in callstacks:
        #    cs.my_loop = self

        for item in self.callstack_list:
            if isinstance(item, loop):
                item.callstack_set_owner_loop()
            elif isinstance(item, conditional_rank_block):
                item.callstack_set_owner_loop(self)
            else:
                item.my_loop = self
                

    def __len__(self):
        return len(self.callstack_list)

    def __eq__(self, other):
        if type(other) == loop:
            return self.iterations == other.iterations
        elif type(other) == callstack:
            return self.callstack_list[0] == other

    def __lt__(self, other):
        if type(other) == loop:
            return self.iterations < other.iterations
        elif type(other) == callstack:
            return self.callstack_list[0] < other

    def __gt__(self, other):
        if type(other) == loop:
            return self.iterations > other.iterations
        elif type(other) == callstack:
            return self.callstack_list[0] > other

    def __le__(self, other):
        if type(other) == loop:
            return self.iterations <= other.iterations
        elif type(other) == callstack:
            return self.callstack_list[0] <= other

    def __ge__(self, other):
        if type(other) == loop:
            return self.iterations >= other.iterations
        elif type(other) == callstack:
            return self.callstack_list[0] >= other

    def __str__(self):
        val  = "> Loop iterations = {0}\n".format(self.iterations)
        val += "> Number of merges = {0}\n".format(self.nmerges)
        val += "> Ranks involved = {0}\n".format(self.get_all_ranks())
        val += "> Common callstack = {0}\n".format(self.common_callstack)

        val = pretty_print(val, "Loop info")

        for callstack in self.callstack_list:
            if type(callstack) == loop:
                val += "-> Subloop\n"
                val += str(callstack)+"\n"
                val += "-> End subloop\n"
            else:
                val += str(callstack)+"\n"

        return val
