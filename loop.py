#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>

*****************************************************************************
*                        ANALYSIS PERFORMANCE TOOLS                         *
*                              [tool name]                                  *
*                         [description of the tool]                         *
*****************************************************************************
*     ___     This library is free software; you can redistribute it and/or *
*    /  __         modify it under the terms of the GNU LGPL as published   *
*   /  /  _____    by the Free Software Foundation; either version 2.1      *
*  /  /  /     \   of the License, or (at your option) any later version.   *
* (  (  ( B S C )                                                           *
*  \  \  \_____/   This library is distributed in hope that it will be      *
*   \  \__         useful but WITHOUT ANY WARRANTY; without even the        *
*    \___          implied warranty of MERCHANTABILITY or FITNESS FOR A     *
*                  PARTICULAR PURPOSE. See the GNU LGPL for more details.   *
*                                                                           *
* You should have received a copy of the GNU Lesser General Public License  *
* along with this library; if not, write to the Free Software Foundation,   *
* Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA          *
* The GNU LEsser General Public License is contained in the file COPYING.   *
*                                 ---------                                 *
*   Barcelona Supercomputing Center - Centro Nacional de Supercomputacion   *
*****************************************************************************
'''


import sys
import numpy as np
import constants



class cluster (object):
    def __init__(self, cluster, ranks):
        self._cluster=cluster
        self._ranks=ranks
        
        # TODO: For all ranks
        ranks_loops=[]
        for rank in range(self._ranks):
            _smatrix,_scs, _mc=cluster2smatrix(self._cluster, rank)
            loops=self.__subloops(_smatrix, _scs, _mc, rank)

            if len(loops) > 1:
                self.__loops_level_merge(self, loops)
            else:
                ranks_loops.append(loops[0])

        # TODO: Ranks merge level
        self.__ranks_level_merge(ranks_loops)

    def str(self):
        return self._merged_rank_loops.str()

    def __subloops(self, smatrix, scs, mc, rank):
        # A times matrix for a cluster can contain more than one loop
        # if there are behaving in the same way. The matrix could looks like
        #
        #   1-loop matrix       2-loops matrix      3-loops matrix
        #   ~ ~ ~ ~             - - - - ~ ~ ~ ~     ~ ~ - - - - - -
        #   ~ ~ ~ ~             ~ ~ ~ ~ - - - -     - - ~ ~ ~ - - -
        #   ~ ~ ~ ~             ~ ~ ~ ~ - - - -     - - - - - ~ ~ ~

        # TODO: Detect how many loops there are and split the matrix
        # NOTE: No estoy seguro de si podria ser un unico bucle con condiciones

        if mc == constants.PURELOOP:
            return [loop(smatrix, scs, rank)]
        else:
            assert False, "It is not developed yet."

    def __loops_level_merge(self, loops):
        assert False, "It is not developed yet."

    def __ranks_level_merge(self, ranks_loops):
        # Merging all ranks with first one
        for i in range(1, len(ranks_loops)):
            ranks_loops[0].merge(ranks_loops[i])

        self._merged_rank_loops=ranks_loops[0]


class loop (object):
    def __init__(self, tmat, cstack, rank):
        self._tmat={}
        self._cs={} # {cs:[..], ranks:[..]}

        self._rank=rank
        self._tmat[rank]=tmat
        self._cstack = cstack
        self._merge = 0

        # The key of every cs set is the line of the first call of the callstack
        dummy,self._loopdeph=cs_uncommon_part(self._cstack)
        key=self._cstack[0] \
            .split(constants._intra_field_separator)[1::2][self._loopdeph]

        self._cs.update({key:{"cs":self._cstack, "ranks":[self._rank]}})

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

    def str(self):

        # For now, we only allow rank mergin, when the number of loops is the
        # same for every rank.
        niters=len(self._tmat[self._rank][0])

        for rank, tmat in self._tmat.items():
            assert len(tmat[0])==niters, "Not all merged ranks have the same iters.)"
   
        pseudocode =constants.FORLOOP.format(
            niters,
            self._cstack[0].split(
                constants._intra_field_separator)[0::2][self._loopdeph])

        cskeys=list(self._cs.keys())
        sorted(cskeys)

        for key in cskeys:
            ranks=self._cs[key]["ranks"]
            cs=self._cs[key]["cs"]

            #suncommon, ibase=cs_uncommon_part(cs)
            #if len(suncommon[0])==0: continue

            suncommon=[]
            for cs in self._cs[key]["cs"]:
                suncommon.append(
                    cs.split(
                        constants._intra_field_separator)[0::2][self._loopdeph+1:])

            #import pdb; pdb.set_trace()

            tabs=0
            if len(ranks) < self._merge:
                tabs+=1
                pseudocode += "  "+constants.INLOOP_STATEMENT \
                    .format(constants.IF.format("rank in "+str(ranks)))



            # Loop body
            lastsc=[]
            for sc in suncommon:
                line=[]
                for i in sc:
                    if not i in lastsc: line.append(i)
                
                ucommon_sc=len(sc)-len(line)+tabs
                callchain="  | "*(ucommon_sc) + line[0] + "()\n"
                for j in range(1,len(line)):
                    callchain+="  " + "  | "*(ucommon_sc+j) + line[j] + "()\n"

                lastsc=sc[:-1]
                callchain="  "+callchain
                pseudocode+=constants.INLOOP_STATEMENT.format(callchain)

        return pseudocode


    def print_iterations(self):
        '''
        print("Cluster {0} have been found {1} iterations]"
                .format(cluster, len(it_cluster)))
        cnt=1
        print("> Iteration_TOT  found @ [ {0} , {1} )"
                .format(it_cluster[0][0], it_cluster[-1][1]))
    
        
        for i in range(len(it_cluster)):
            print(" - Iteration_{0} found @ [ {1} , {2} )"
                    .format(cnt,it_cluster[i][0],it_cluster[i][1]))
            cnt+=1
        '''
        pass


############################
#### AUXILIAR FUNCTIONS ####
############################

def cs_uncommon_part(scalls):
    # odd positions have the lines meanwhile even possitions have calls

    # We can expect that all the stack before the loop is equal, then
    # the loop is exactly in the first call when the lines differs.
    # The rest of calls are from the loop.

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



def cuadra(mat):
    # Fill the gaps at end of modified rows
    maxcols=len(mat[0])
    for row in range(len(mat)):
        if len(mat[row]) < maxcols:
            mat[row].extend([0]*(maxcols-len(mat[row])))
        elif len(mat[row]) > maxcols:
            maxcols=len(mat[row])
            rr=row
            while rr >=0:
                mat[rr].extend([0]*(maxcols-len(mat[rr])))
                rr-=1


# This function performs all the matrix transformation (gaps add) needed
# in order to guarantee the constraint of iterations non-overlaping.
# i.e. the last element of col n must be less or equal that the first
# element of n+1 col
def boundaries_sort_2(tmat):
    mat=tmat.tolist()

    mheight=len(mat)
    mwidth=len(mat[0])

    last=mat[0][0]
    lastcol=0
    lastrow=0

    i=0
    matrix_complexity=0
    # 0: there are no holes, therefore all iterations all equal
    # 1: are holes but all of them are concentrated in areas, therefore in this cluster
    #    there are more than one loop
    # 2: The holes are diseminated over all matrix with a certain pattern. 
    #    There are some conditional statements in iterations.
    # TODO: For the moment 1 means only that there are holes

    while i < len(mat[0]):
        for j in range(mheight):
            if mat[j][i]==0: continue
            if mat[j][i] < last:
                matrix_complexity=1
                jj=lastrow
                while mat[jj][lastcol] > mat[j][i]:
                    mat[jj].insert(lastcol,0)
                    jj-=1
                    if jj < 0: break

            lastcol=i
            lastrow=j
            last=mat[j][i]
        cuadra(mat)
        i+=1

    
    # Remove last empty cols
    minzeros=sys.maxint
    for row in mat:
        zeros=0
        for i in range(-1,-len(row)+1, -1):
            if row[i]!=0: break
            zeros+=1

        if zeros < minzeros: 
            minzeros=zeros

    if minzeros > 0:
        for row in mat:
            del row[-minzeros:]

    return mat, matrix_complexity


def cluster2mat(rank, cluster):
    keys_cs=[]
    index=0
    max_size=0

    tomat=[]

    cs_map={}
    for cs in cluster:
        k=cs.keys()[0]
        
        if int(cs[k]["rank"]) != rank: continue

        cs_map.update({cs[k]["when"][0]:k})

        if len(cs[k]["when"]) > max_size:
            max_size=len(cs[k]["when"]) 
            for i in range(index-1, -1, -1):
                holes=max_size-len(tomat[i])
                tomat[i].extend([constants._empty_cell]*holes)
        elif len(cs[k]["when"]) < max_size:
            holes=max_size-len(cs[k]["when"])
            cs[k]["when"].extend([constants._empty_cell]*holes)

        tomat.append(cs[k]["when"])
        keys_cs.append(k)
        index+=1

    return np.matrix(tomat),max_size,cs_map

# This function get a cluster (set of callstacks and occurrences)
# and generate a sorted matrix. The sorted is done by sorting the columns
# in such way that the las value of column N is less or equal that the
# first value of column N+1. It means that the columns can be divided into
# subsets on every subset is an iteration.
#
# RETURN: tmat         : The matrix of occurrences of calls
#         keys_ordered : Callstacks ordered in such way that the callstack in
#                        position y is the callstack that have its occurrences
#                        on times in row y of the 'tmat'.
#         mcomplexity  : ...

def cluster2smatrix(cluster, rank):
    tmat,xsize,cs_map=cluster2mat(rank, cluster)

    # Sorting by the first column
    tmat=tmat.view("i8,"*(xsize-1)+"i8")
    tmat.sort(order=["f0"], axis=0)
    tmat=tmat.view(np.int)

    # Get the callstacks ordered by first occurrence
    keys_ordered=[]
    for row in tmat.tolist():
        keys_ordered.append(cs_map[row[0]])

    # Adding holes if needed
    tmat, mcomplexity=boundaries_sort_2(tmat)

    #print_matrix(tmat, True)
    return tmat, keys_ordered, mcomplexity
'''
    iterations=[]
    if mcomplexity==0:
        # simple case
        

        pass
    else:
        # complex case

        mheight=len(tmat)
        mwidth=len(tmat[0])
      
        print_matrix(tmat, True)

        # It is defined by the row. 
        # Remember that every row corresponds to a different call
        last_calls=[0]; ini_it=tmat[0][0]

        for j in range(mwidth):
            for i in range(mheight):
                if tmat[i][j]==0:continue
                if i in last_calls and j!=0:
                    fin_it=tmat[i][j]
                    iterations.append((ini_it,fin_it))
                    ini_it=fin_it
                    last_calls=[i]
                else:
                    last_calls.append(i)

        # Last iteration
        iterations.append((ini_it, tmat[i][j]))

    return iterations, keys_ordered
    #return tmat.tolist()[0][:-1], keys_ordered 
'''

