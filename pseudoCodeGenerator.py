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

def print_matrix(matrix, infile):
    if type(matrix)==list:
        mat=matrix
    else:
        mat=matrix.tolist()

    def format_nums(val):
        return str(val).zfill(12)

    if infile:
        filen=int(np.random.rand()*1000)
        filename="matrix_{0}.txt".format(filen)
        print("---> SAVING TO {0}".format(filename))

        ff=open(filename, "w")
        for row in mat:
            ff.write("\t".join(map(format_nums,row)))
            ff.write("\n")
        ff.close()
    else:
        for row in mat:
            print("\t".join(map(format_nums,row)))


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



def cs_uncommon_part(scalls):
    # odd positions have the lines meanwhile even possitions have calls

    '''
    result=[]
    loopbodypos=0
    howmany=0
    for i in range(1, len(scalls)):
        csprev_lines=scalls[i-1].split(constants._intra_field_separator)[1::2]
        cscurr_lines=scalls[i].split(constants._intra_field_separator)[1::2]

        csprev_calls=scalls[i-1].split(constants._intra_field_separator)[0::2]
        cscurr_calls=scalls[i].split(constants._intra_field_separator)[0::2]


        its=max(len(csprev_lines),len(cscurr_lines))
        for j in range(its):
            if csprev_lines[j] != cscurr_lines[j]:
                new_loopbodypos=j-1
                break
         
        if new_loopbodypos != loopbodypos:
            if howmany > 0:
                result.append((loopbodypos,howmany))
            loopbodypos=new_loopbodypos
            howmany=1

        howmany+=1

    result.append((loopbodypos, howmany))

    return result
    
    '''
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


def matrix2pseudo_pure(mat, scalls):
    
    # Get the uncommon part of the callstacks
    suncommon,ibase=cs_uncommon_part(scalls)

    # Printing loop statement
    niters=len(mat[0])
    pseudocode =constants.FORLOOP.format(
            niters,
            scalls[0].split(constants._intra_field_separator)[0::2][ibase])

    # TODO: Sort calls in the loop by line

    # Printing loop body
    lastsc=[]
    for sc in suncommon:

        line=[]
        for i in sc:
            if not i in lastsc: line.append(i)
        
        ucommon_sc=len(sc)-len(line)
        callchain="  | "*(ucommon_sc) + line[0] + "()\n"
        for j in range(1,len(line)):
            callchain+="  " + "  | "*(ucommon_sc+j) + line[j] + "()\n"

        lastsc=sc[:-1]
        callchain="  "+callchain
        pseudocode+=constants.INLOOP_STATEMENT.format(callchain)

    return pseudocode



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

def cluster2smatrix(cluster):
    # For the moment, only for rank 0
    tmat,xsize,cs_map=cluster2mat(0, cluster)

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
    

