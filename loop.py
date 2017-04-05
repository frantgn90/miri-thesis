#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, random, logging
import numpy as np
import constants
from temp_matrix import tmatrix

import pdb

class loop (object):
    def __init__(self, tmat, cstack, rank):
        self._tmat={}
        self._cs={}

        self._rank=rank
        self._tmat[rank]=tmat
        self._cstack = cstack
        self._merge = 1 # myself
        self._first_line = 0
        self._is_condition = False
        self._condition_propability = 0

        self._iterations = len(self._tmat[self._rank][0])
        self._original_iterations = self._iterations

        assert self._iterations > 1

        # The key of every cs set is the line of the first call of the callstack
        dummy,self._loopdeph=cs_uncommon_part(self._cstack)

        key=self._cstack[0].split(
                constants._intra_field_separator)[1::2][self._loopdeph]
        self._first_line = key
        self._cs.update({
            int(key):{"cs":list(self._cstack), 
                 "ranks":[self._rank]}})

        logging.debug("New loop with {0} iterations.".format(self._iterations))

    def get_tmat(self):
        return self._tmat[self._rank]

    def get_ranks(self):
        ranks=[]
        for k,v in self._cs.items():
            ranks.extend(v["ranks"])

        return list(set(ranks)) # Removing repetitions

    def merge(self, oloop):
        # Assert if it loop has not been merged before
        assert len(oloop._cs) == 1, "TODO: Merge merged loops (tree-merge)"

        newcs = oloop._cstack
        newrank = oloop._rank

        self._tmat[newrank] = oloop._tmat[newrank]

        for key, cset in self._cs.items():
            if len(newcs) == 0: break
            if newrank in cset["ranks"]: continue

            commoncs = self.__get_common_cs(cset["cs"], newcs)
            uncommoncs_a = self.__substract_cs(cset["cs"],commoncs)

            if len(commoncs) == len(cset["cs"]):
                cset["ranks"].append(newrank)
            elif len(commoncs) > 0 and len(commoncs) < len(cset["cs"]):           
                # Update uncommon cset
                cset["cs"] = uncommoncs_a
                newkey=int(cset["cs"][0] \
                    .split(constants._intra_field_separator)[1::2][self._loopdeph])

                if key != newkey:
                    self._cs[newkey]=dict(self._cs[key]) # copy
                    del(self._cs[key]) # removing the old entry

                # Create common new cset
                newkey=commoncs[0]\
                        .split(constants._intra_field_separator)[1::2][self._loopdeph]
                newcset=list(cset["ranks"]) # copy
                newcset.append(newrank)
                self._cs.update({
                    int(newkey):{ 
                        "cs": commoncs, 
                        "ranks": newcset}})

            # Every time a part of this newcs is merged, then it have to be
            # substracted in order to no merge it again
            newcs = self.__substract_cs(newcs, commoncs)

        # If we check all the actual cs and there is no any coincidence for 
        # some calls, then, we have to create a new cs group
        if len(newcs) > 0: 
                newkey=newcs[0] \
                    .split(constants._intra_field_separator)[1::2][self._loopdeph]
                self._cs.update({
                    int(newkey):{"cs": newcs,
                            "ranks": [newrank]}})

        self._merge += 1

        cskeys=list(self._cs.keys())
        sorted(cskeys)

        # Every time a merge is done, recompute the first line
        self._first_line = cskeys[0]

    def recompute_first_line(self, looplevel):
        cskeys=list(self._cs.keys())
        cskeys.sort(key=float)
        firstk=cskeys[0]

        if type(self._cs[firstk]["cs"]) == loop:
            self._first_line = self._cs[firstk]["cs"]\
                .recompute_first_line(looplevel)
        elif type(self._cs[firstk]["cs"][0]) == loop:
            self._first_line = self._cs[firstk]["cs"][0]\
                .recompute_first_line(looplevel)
        else:
            self._first_line=self._cs[firstk]["cs"][0]\
                .split(constants._intra_field_separator)[1::2][looplevel]

        return self._first_line

    def merge_subloop(self, subloop):
        subranks = subloop.get_ranks()
        # It means that potentially, the subloop will be placed here.
        # Is important to recompute the keys of the cs at the subloop
        # because the level of loop base (i.e. shared calls) in subloop
        # will be potentially highest than the superloop

        subloop.recompute_first_line(self._loopdeph)


        if subloop._iterations < self._iterations:
            subloop._is_condition = True # Maybe a loop into a condition
            subloop._condition_propability = float(subloop._iterations)/self._iterations
        else:
            subloop._iterations/=self._iterations

        # TODO: It should return an 'int'
        subloop_first_line = int(subloop.getFirstLine()) 
        done=False
        keys_sorted = sorted(self._cs.keys(), reverse=True)
        
        # From bottom to top
        done = False
        for k in keys_sorted:
            if done: break

            v=self._cs[k]
            superranks = v["ranks"]

            allranks = (subranks==superranks)

            # TODO: When allranks is false, it still could form part of the
            # superloop but with an extra conditional that is the subset
            subset = set.intersection(*[set(subranks),set(superranks)])
            subset = list(subset)


            # Init line block
            if type(v["cs"][0])==loop:
                v["cs"][0].recompute_first_line(self._loopdeph)
                init_line_block = int(v["cs"][0].getFirstLine())
            else:
                callstack=v["cs"][0].split(constants._intra_field_separator)
                init_line_block = int(callstack[1::2][self._loopdeph])

            # If its place is in/between this block
            #if subloop_first_line >= init_line_block:
            #pdb.set_trace()

            if allranks:
                for i, callstack in zip(range(len(v["cs"])),v["cs"])[::-1]:
                    if done: break
                    cs_fields = callstack.split(constants._intra_field_separator)
                    cs_line = int(cs_fields[1::2][self._loopdeph])

                    if subloop_first_line == cs_line:
                        for next_loopdeph in range(self._loopdeph+1,len(cs_fields[1::2])):
                            if done: break
                            cs_next_level_line = cs_fields[1::2][next_loopdeph]
                            cs_next_level_call = cs_fields[0::2][next_loopdeph]

                            subloop_next_line = subloop.get_first_line_at_level(
                                    next_loopdeph)
                            subloop_next_call = subloop.get_first_call_at_level(
                                    next_loopdeph)


                            assert cs_next_level_call == subloop_next_call

                            if cs_next_level_line > subloop_next_line:
                                v["cs"].insert(i, subloop)
                                done = True
                            elif cs_next_level_line < subloop_next_line:
                                v["cs"].insert(i+1, subloop)
                                done = True

                    elif subloop_first_line > cs_line:
                        v["cs"].insert(i+1, subloop)
                        done = True
                
                if not done:
                    v["cs"].insert(0, subloop)
                    done = True
            else:
                after_rank_line = -1
                after_rank_block = []

                for callstack in v["cs"]:
                    cs_fields = callstack.split(constants._intra_field_separator)
                    cs_line = int(cs_fields[1::2][self._loopdeph])
                    
                    if subloop_first_line == cs_line:
                        print("WARNING: Deeper levels of the callstacks"\
                                " must be checked the order of the calls"\
                                "could be disordered. (2)")
                    if subloop_first_line < cs_line:
                        after_rank_block.append(callstack)
                        if after_rank_line == -1: after_rank_line = cs_line

                # Insert the subloop in the middle of a block
                self._cs.update({
                    subloop_first_line: 
                        {"cs":[subloop], "ranks": subloop.get_ranks()}})

                # The block has been splitted. This is the second part.
                if after_rank_line != -1:
                    self._cs.update({
                        after_rank_line:
                            {"cs":after_rank_block, "ranks": v["ranks"]}}) 
                done=True
                break
            
        assert done

    def __get_common_cs(self, cs1, cs2):
        res=[]
        for cs in cs1:
            if cs in cs2:
                res.append(cs)

        return res

    def __substract_cs(self, cs1, cs2):
        res=[]
        for cs in cs1:
            if not cs in cs2:
                res.append(cs)

        return res

    def str(self,block_tabs, base):
        relative_tabs=0

        ##############################################################
        # Printing the path from the previous level loop to this one #
        ##############################################################

        loop_base_from=""
        if base <= self._loopdeph:
            loop_base_from=constants.TAB*relative_tabs\
                    + self._cstack[0].split(constants._intra_field_separator)\
                        [0::2][base]+"()\n"
        
            relative_tabs+=1

        for lb in range(base+1, self._loopdeph+1):
            loop_base_from+=constants.TAB*relative_tabs\
                    + self._cstack[0].split(constants._intra_field_separator)\
                        [0::2][lb]+"()\n"
            relative_tabs+=1

        pseudocode=loop_base_from

        #############################
        # Printing loop description #
        #############################

        loop_base=self._cstack[0].split\
                (constants._intra_field_separator)[0::2][self._loopdeph]

        if self._is_condition == False:
            pseudocode+=constants.TAB*(relative_tabs)\
                 + constants.FORLOOP.format(
                         self._iterations)
        else:
            pseudocode+=constants.TAB*(relative_tabs)\
                + constants.IF_DATA.format(self._condition_propability)


        relative_tabs+=1

        ######################
        # Printing loop body #
        ######################

        cskeys=list(self._cs.keys())
        cskeys.sort(key=float)

        some_if=False
        for key in cskeys:
            ranks=self._cs[key]["ranks"]
            cs=self._cs[key]["cs"]

            assert type(self._cs[key]["cs"])!=loop,\
                    "CS can not be a loop"

            suncommon=[]
            for cs in self._cs[key]["cs"]:
                if type(cs) == loop:
                    suncommon.append(cs)
                else:
                    suncommon.append(cs.split(constants.\
                            _intra_field_separator)[0::2][self._loopdeph+1:])

            #####################
            # Ranks conditional #
            #####################
            if_tabs=0
            if len(ranks) < self._merge:
                if some_if == True:
                    pseudocode += constants.TAB*relative_tabs\
                        + constants.ELSE_RANK.format(ranks)
                else:
                    # TODO: Not should be elif for all cases.. only for those
                    # cases that the conditions are completely complementary
                    some_if=True
                    pseudocode += constants.TAB*relative_tabs\
                        + constants.IF_RANK.format(ranks)

                if_tabs=1
                #relative_tabs+=1

            # Loop body calls
            lastsc=[]
            rel_relative_tabs=0
            callchain=""
            for sc in suncommon:
                if type(sc) == loop:
                    loop_pseudocode, dummy=sc.str(
                            rel_relative_tabs, 
                            self._loopdeph+1)
                    callchain += loop_pseudocode
                    lastsc=dummy[:-1]
                else:

                    if len(sc) == 0: continue
                    line=[]
                    for i in sc:
                        if not i in lastsc: 
                            line.append(i)

                    n_common_calls=len(sc)-len(line)
                    rel_relative_calls=n_common_calls
    
                    # First call of the callchain
                    callchain+=constants.TAB*rel_relative_calls\
                            + line[0] +"()\n"

                    #rel_relative_calls+=1

                    for j in range(1,len(line)):
                        callchain+= constants.TAB*(rel_relative_calls+j)\
                                + line[j]+"()\n"
                    
                    # If there is more than one call to the same function
                    # we want to see it more than one time
                    lastsc=sc[:-1]


            callchain=constants.TAB*(relative_tabs+if_tabs)\
                    + callchain.replace("\n",
                            "\n"+constants.TAB*(relative_tabs+if_tabs))
            # Removing the last newline tabulations
            callchain=callchain[:-(len(constants.TAB*(relative_tabs+if_tabs)))]
            pseudocode+=callchain
                    
        # Adding the block tabulation
        pseudocode=constants.TAB*block_tabs \
                + pseudocode.replace("\n", "\n"+constants.TAB*block_tabs)
        #pseudocode=pseudocode[:-(len(constants.TAB*block_tabs))]

        # When return from a subloop we want to know at which level this subloop
        # has been executed
        complete_lastsc=self.getLastSc(base)
        return pseudocode, complete_lastsc

    def getFirstLine(self):
        return self._first_line

    def getLastSc(self, base):
        cskeys=list(self._cs.keys())
        cskeys.sort(key=float)

        if type(self._cs[cskeys[-1]]["cs"])==loop: # NOTE: Not sure about it
            return self._cs[cskeys[-1]]["cs"].getLastSc(base)
        elif type(self._cs[cskeys[-1]]["cs"][-1])==loop:
            return self._cs[cskeys[-1]]["cs"][-1].getLastSc(base)
        else:
            return self._cs[cskeys[-1]]["cs"][-1]\
                .split(constants._intra_field_separator)[0::2][base:]


    def getIteration(self, rank, it):
        assert it < len(self._tmat[rank][0]), "This iteration does not exist."
        return [self._tmat[rank][0][it], self._tmat[rank][0][it+1]]

    def get_first_line_at_level(self, level):
        stack_lines = self._cstack[0].split(constants._intra_field_separator)[1::2]
        return stack_lines[level]

    def get_last_line_at_level(self, level):
        stack_lines = self._cstack[-1].split(constants._intra_field_separator)[1::2]
        return stack_lines[level]

    def get_first_call_at_level(self, level):
        stack_calls = self._cstack[0].split(constants._intra_field_separator)[0::2]
        return stack_calls[level]

    def get_last_call_at_level(self, level):
        stack_calls = self._cstack[-1].split(constants._intra_field_separator)[0::2]
        return stack_calls[level]



############################
#### AUXILIAR FUNCTIONS ####
############################

def cs_uncommon_part(scalls):
    # odd positions have the lines meanwhile even possitions have calls

    # We can expect that all the stack before the loop are equal, then
    # the loop is exactly in the first call when the lines differs.
    # The rest of calls are from the loop.

    if len(scalls)==1: 
        level=0
        find = False
        for call in scalls[0].split(constants._intra_field_separator)[0::2]:
            if call == "main":
                find = True
                break
            level+=1

        if not find:
            level = 0

        return scalls[0].split(constants._intra_field_separator), level

    pos=0
    globpos=len(scalls[0].split(constants._intra_field_separator))

    # TODO: Not just look at line, also to function!!
    for i in range(1,len(scalls)):
        csprev_lines=scalls[i-1].split(constants._intra_field_separator)[1::2]
        cscurr_lines=scalls[i].split(constants._intra_field_separator)[1::2]

        iterations=max(len(csprev_lines),len(cscurr_lines))
        for j in range(iterations):
            if csprev_lines[j] != cscurr_lines[j]:
                pos=j
                break

        assert(pos != iterations)

        if pos < globpos:
            globpos=pos


    result=[]
    for cs in scalls:
        calls=cs.split(constants._intra_field_separator)[0::2]
        result.append(calls[globpos+1:]) # globpos+1
        
    return result, globpos # globpos
