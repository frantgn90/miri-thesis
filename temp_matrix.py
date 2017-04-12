#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright ÃÂ© 2016 Juan Francisco MartÃÂ­nez <juan.martinez[AT]bsc[dot]es>

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

#########################
# Temporal matrix class #
#########################

class tmatrix(object):
    def __init__(self, matrix, callstacks, transformations):
        self._matrix=matrix
        self._transformations=transformations
        self._sorted_callstacks=callstacks

    @classmethod
    def fromMatrix(cls, matrix):
        sorted_matrix, transformations = cls.__boundaries_sort(matrix)
        return cls(matrix=sorted_matrix,
                   callstacks=None,
                   transformations=transformations)

    @classmethod
    def fromCallstackList(cls, callstacks_list):
        matrix, cs_map = cls.__get_matrix(callstacks_list)
        
        # Get the callstacks ordered by first occurrence
        keys_ordered=[]
        for row in matrix.tolist():
            keys_ordered.append(cs_map[row[0]])

        # Adding holes if needed
        sorted_matrix, transformations = cls.__boundaries_sort(matrix)

        return cls(matrix=sorted_matrix, 
                   callstacks=keys_ordered, 
                   transformations=transformations)

    def getMatrix(self):
        return self._matrix

    def getPartitions(self):
        subm_map = self.__submatrix(self._matrix)

        times_partitions=[]
        calls_partitions=[]

        for sh_rows, sh_cols in subm_map.items():
            part=[]
            for i in range(sh_rows[1]-sh_rows[0]+1): part.append([])
            for row in range(sh_rows[0], sh_rows[-1]+1):
                for cols in sh_cols:
                    data = self._matrix[row][cols[0]:cols[1]+1]
                    part[row-sh_rows[0]].extend(data)
            times_partitions.append(part)
            calls_partitions.append(self._sorted_callstacks[sh_rows[0]:sh_rows[1]+1])

        result=[]
        for i in range(len(calls_partitions)):
            result.append(
                    tmatrix(times_partitions[i],calls_partitions[i], 0))

        return result

    def isTransformed(self):
        return self._transformations == 1

    def getCallstacks(self):
        return self._sorted_callstacks

    @classmethod
    def __get_matrix(self, callstacks_list):
        keys_cs=[]; tomat=[]; index=0; max_size=0 

        cs_map={}
        for cs in callstacks_list:
            k=cs.keys()[0]
            
            # TODO: Eventually they can happen at same first time
            # so the key is not completelly unique. Use the position of the list
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
    

        tmat=np.matrix(tomat)

        # Sorting by the first column
        tmat=tmat.view("i8,"*(max_size-1)+"i8")
        tmat.sort(order=["f0"], axis=0)
        tmat=tmat.view(np.int)

        return tmat, cs_map



    # This function performs all the matrix transformation (gaps add) needed
    # in order to guarantee the constraint of iterations non-overlaping.
    # i.e. the last element of col n must be less or equal that the first
    # element of n+1 col

    @classmethod
    def __boundaries_sort(cls, tmat):
        mat=tmat.tolist()

        mheight=len(mat)

        last=mat[0][0]
        lastcol=lastrow=col=0
        transformed=0
    
        while col < len(mat[0]):
            for row in range(mheight):
                if mat[row][col]==0: continue
                if mat[row][col] < last:
                    transformed=1
                    jj=lastrow
                    while mat[jj][lastcol] > mat[row][col]:
                        mat[jj].insert(lastcol,0)
                        jj-=1
                        if jj < 0:
                            col-=1;break
                lastcol=col
                lastrow=row
                last=mat[row][col]
            cls.__cuadra(mat)
            col+=1

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

        return mat, transformed


    @classmethod
    def __cuadra(cls, mat):
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

    def __submatrix(self, mat):
            subm=[]

            min_v=float("inf")
            min_h=float("inf")

            for i in range(len(self._matrix)):
                for j in range(len(self._matrix[0])):
                    
                    already_explored=False
                    # Already explored i
                    for sm in subm:
                        if i >= sm[1][0] and i <= sm[1][1] and \
                           j >= sm[0][0] and j <= sm[0][1]:
                            already_explored=True
                            break

                    if not already_explored and self._matrix[i][j] != 0: # Void cell
                        v=h=0

                        # Horitzontal min
                        for ii in range(i, len(self._matrix)):
                            if self._matrix[ii][j] == 0: break
                            for jj in range(j, len(self._matrix[0])):
                                if self._matrix[ii][jj] != 0:
                                    h+=1
                                else: break
                            if h < min_h: min_h=h

                        # Vertical min
                        for jj in range(j,len(self._matrix[0])):
                            if self._matrix[i][jj] == 0: break;
                            for ii in range(i, len(self._matrix)):
                                if self._matrix[ii][jj] != 0:
                                    v+=1
                                else: break
                            if v < min_v: min_v=v

                        subm.append([(j,j+min_h-1),(i,i+min_v-1)])

            # Now group submatrixes into loops
            if len(subm) > 1:
                # Merge all submatrix that shares rows
                subm_merge = {}
                for sm in subm:
                    rows = sm[1]
                    cols = sm[0]

                    if rows in subm_merge:
                        subm_merge[rows].append(cols)
                    else:
                        subm_merge.update({rows:[cols]})

            return subm_merge

            # If all partitions are completelly disyunctive and can explain all 
            # the matrix, it means that every partition is a loop
            # TODO: Think about complex cases with conditionals...

#            disyunctive=True
#
#            visited_rows=[]
#            visited_cols=[]
#
#            for s in subm:
#                # Let's test the rows
#
#                rows_range=s[1]
#                for i in range(rows_range[0], rows_range[1]):
#                    if not i in visited_rows:
#                        visited_rows.append(i)
#                    else:
#                        disyunctive=False
#                        break
#
#                # Let's test the cols
#                
#                cols_range=s[0]
#                for i in range(cols_range[0], cols_range[1]):
#                    if not i in visited_cols:
#                        visited_cols.append(i)
#                    else:
#                        disyunctive=False
#                        break
#                
#
#            if len(visited_rows)==len(mat[0]) and \
#                    len(visited_cols)==len(mat):
#                        completed=True
#            else:
#                completed=False
#
#            if completed and disyunctive:
#                # The partitioned matrixes have to be returned
#                res=[]
#                rescs=[]
#                for s in subm:
#                    pmat=[]
#                    for i in range(s[1][0], s[1][1]):
#                        pmat.append(mat[i][s[0][0]:(s[0][1])])
#                    
#                    res.append(pmat)
#                    rescs.append(self._sorted_callstacks[s[1][0]:s[1][1]])
#            else:
#                res=[mat]
#                rescs=[self._sorted_callstacks]
#
#            return res, rescs

