#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, random
import numpy as np
import constants
from temp_matrix import tmatrix

import pdb

class loop (object):
    def __init__(self, tmat, rank):
        self._tmat={}
        self._cs={} # {cs:[..], ranks:[..]}

        self._rank=rank
        self._tmat[rank]=tmat
        self._cstack = cstack
        self._merge = 1 # myself
        self._first_line = 0

        self._iterations = len(self._tmat[self._rank][0])

        #import pdb; pdb.set_trace()
    
        # The key of every cs set is the line of the first call of the callstack
        dummy,self._loopdeph=cs_uncommon_part(self._cstack)

        #pdb.set_trace()
        key=self._cstack[0] \
            .split(constants._intra_field_separator)[1::2][self._loopdeph]

        self._first_line = key
        self._cs.update({key:{"cs":list(self._cstack), "ranks":[self._rank]}})

    def get_tmat(self):
        return self._tmat[self._rank]

    def get_ranks(self):
        ranks=[]
        for k,v in self._cs.items():
            ranks.extend(v["ranks"])

        return list(set(ranks)) # Removing repetitions

    def merge(self, oloop):
        assert len(oloop._cs) == 1, "TODO: Merge merged loops (tree-merge)"

        newcs = oloop._cstack
        newrank = oloop._rank

        self._tmat[newrank] = oloop._tmat[newrank]
    
        # print("MERGING {0} with {1}".format(self._rank, newrank))

        for key, cset in self._cs.items():
            if len(newcs) == 0: break
            if newrank in cset["ranks"]: continue

            commoncs = self.__get_common_cs(cset["cs"], newcs)
            uncommoncs_a = self.__substract_cs(self._cs[key]["cs"],commoncs)
            uncommoncs_b = self.__substract_cs(newcs, commoncs)

            if len(commoncs) == len(cset["cs"]): # all is common
                self._cs[key]["ranks"].append(newrank)
            elif len(commoncs) > 0 and len(commoncs) < len(cset["cs"]):

                # Create common new cset
                newkey=commoncs[0] \
                    .split(constants._intra_field_separator)[1::2][self._loopdeph]
                newcset=list(cset["ranks"]) # copy
                newcset.append(newrank)
                self._cs.update({
                    newkey:{ 
                        "cs": commoncs, 
                        "ranks": newcset}})

                # Update uncommon cset
                self._cs[key]["cs"] = uncommoncs_a
                newkey=self._cs[key]["cs"][0] \
                    .split(constants._intra_field_separator)[1::2][self._loopdeph]


                if key != newkey:
                    self._cs[newkey]=dict(self._cs[key]) # copy
                    del(self._cs[key]) # removing the old entry

            # Every time a part of this newcs is merged, then it have to be
            # substracted in order to no merge it again
            newcs = self.__substract_cs(newcs, commoncs)

        # If we check all the actual cs and there is no any coincidence for 
        # some calls, then, we have to create a new cs group
        if len(newcs) > 0: 
                newkey=newcs[0] \
                    .split(constants._intra_field_separator)[1::2][self._loopdeph]
                self._cs.update({
                    newkey:{
                    "cs": newcs,
                    "ranks": [newrank]}})

        self._merge += 1

        cskeys=list(self._cs.keys())
        sorted(cskeys)

        # Every time a merge is done, recompute the first line
        self._first_line = cskeys[0]

    def recomputeFirstLine(self, looplevel):
        '''
        for k,v in self._cs.items():
            # With the first one is enough
            newkey=v["cs"][0].split(constants._intra_field_separator)[1::2][looplevel]
            
            if newkey!=k:
                self._cs[newkey] = self._cs[k]
                self._cs.pop(k)
        
        cskeys=list(self._cs.keys())
        sorted(cskeys)
        self._first_line = cskeys[0]
        '''

        cskeys=list(self._cs.keys())
        cskeys.sort(key=float)
        firstk=cskeys[0]

        self._first_line=self._cs[firstk]["cs"][0]\
                .split(constants._intra_field_separator)[1::2][looplevel]

    def mergeS(self, subloop):
        subranks = subloop.get_ranks()
        # It means that potentially, the subloop will be placed here.
        # Is important to recompute the keys of the cs at the subloop
        # because the level of loop base (i.e. shared calls) in subloop
        # will be potentially highest than the superloop

        subloop.recomputeFirstLine(self._loopdeph)
        subloop._iterations/=self._iterations
        sline = subloop.getFirstLine()

        # This subloop has to be pushed in some place, inside a set of 
        # callstacks that is a superset of sranks.

        done=False
        for k,v in self._cs.items():
            superranks = v["ranks"]
            #superset = (set(superranks).intersection(subranks)==set(subranks))
            superset = (subranks==superranks)

            if superset:
                # TODO: Speedup search by dicotomical search
                inject_at=0
                for i in range(len(v["cs"])):
                    if type(v["cs"][i])==loop:
                        v["cs"][i].recomputeFirstLine(self._loopdeph)
                        line=v["cs"][i].getFirstLine()
                    else:
                        callstack=v["cs"][i].split(constants._intra_field_separator)
                        line = callstack[1::2][self._loopdeph]

                    if int(line) > int(sline):
                        v["cs"].insert(i, subloop)
                        done=True; break
                    elif int(line) == int(sline):
                        for j in range(self._loopdeph,len(callstack[0::2])):
                            subloop.recomputeFirstLine(j)
                            new_line=callstack[1::2][j]
                            new_sline=subloop.getFirstLine()

                            if int(new_sline) < int(new_line):
                                v["cs"].insert(i, subloop)
                                done=True; break;

                if not done:
                    done=True
                    v["cs"].append(subloop)

            if done: break

        # If the execution arrives here without injecting the subloop, then
        # it means that we need to create a new callstack group
        if not done:
            self._cs.update({sline:{ "cs": subloop, "ranks": subranks}})

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
        #if self._rank == 0:
        #print self._cs
        #print

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

        pseudocode+=constants.TAB*(relative_tabs)\
                + constants.FORLOOP.format(self._iterations,loop_base)

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

            if type(self._cs[key]["cs"])==loop:
                '''
                loop_pseudocode, dummy=self._cs[key]["cs"].str(rel_relative_tabs, 
                            self._loopdeph+1)
                pseudocode += loop_pseudocode
                lastsc=dummy[:-1]
                continue
                '''
                assert False, "CHECK IT OUT: Strange situation"

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
                        + constants.ELSE.format("rank in "+str(ranks))
                else:
                    # TODO: Not should be elif for all cases.. only for those
                    # cases that the conditions are completely complementary
                    some_if=True
                    pseudocode += constants.TAB*relative_tabs\
                        + constants.IF.format("rank in "+str(ranks))


                if_tabs=1
                #relative_tabs+=1

            # Loop body calls
            lastsc=[]
            rel_relative_tabs=0
            callchain=""
            for sc in suncommon:
                if type(sc) == loop:
                    loop_pseudocode, dummy=sc.str(rel_relative_tabs, 
                            self._loopdeph+1)
                    callchain += loop_pseudocode
                    lastsc=dummy[:-1]
                else:
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


############################
#### AUXILIAR FUNCTIONS ####
############################

def cs_uncommon_part(scalls):
    # odd positions have the lines meanwhile even possitions have calls

    # We can expect that all the stack before the loop is equal, then
    # the loop is exactly in the first call when the lines differs.
    # The rest of calls are from the loop.

    if len(scalls)==1: 
        level=0
        for call in scalls[0].split(constants._intra_field_separator)[0::2]:
            if call == "main": 
                break
            level+=1
        return scalls[0].split(constants._intra_field_separator), level

    pos=0
    globpos=len(scalls[0].split(constants._intra_field_separator))

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
