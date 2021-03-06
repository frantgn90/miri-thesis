#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys
import numpy as np

import constants

class tmatrix(object):
    def __init__(self, matrix, callstacks, transformations):
        self._matrix=matrix
        self._transformations=transformations
        self._sorted_callstacks=callstacks
        self._hidden_superloop=False
        self._hidden_superloop_its=0

    @classmethod
    def fromMatrix(cls, matrix):
        sorted_matrix, transformations = cls.__boundaries_sort(matrix)
        return cls(sorted_matrix, None, transformations)

    @classmethod
    def from_callstacks_obj(cls, callstacks):
        scallstacks = sorted(callstacks, key=lambda x: x.instants[0])
        #scallstacks = sorted(callstacks)
        matrix = [x.instants for x in scallstacks]
        sorted_matrix, transformations = cls.__boundaries_sort(matrix)

        #visible = ""
        #for cs,tt in zip(scallstacks,sorted_matrix):
        #    times = str(list(map(lambda x: 'X' if x != 0 else '0', tt)))
        #    visible += "{0:>50} {1}\n".format(str(cs), times)
        #print (visible)
        return cls(sorted_matrix, scallstacks, transformations)

    def is_hidden_superloop(self):
        return self._hidden_superloop

    def get_hidden_superloop_its(self):
        return self._hidden_superloop_its

    def getMatrix(self):
        return self._matrix

    def get_subloops(self):
        subm_map = self.__submatrix(self._matrix)

        calls_partitions=[]
        for sh_rows, sh_cols in subm_map.items():
            part=[]
            for i in range(sh_rows[1]-sh_rows[0]+1): part.append([])
            for row in range(sh_rows[0], sh_rows[-1]+1):
                for cols in sh_cols:
                    data = self._matrix[row][cols[0]:cols[1]+1]
                    part[row-sh_rows[0]].extend(data)
            calls_partitions.append(self._sorted_callstacks[sh_rows[0]:sh_rows[1]+1])

        return calls_partitions

    def aliased(self):
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
        if type(tmat) != list:
            mat=tmat.tolist()
        else:
            mat=tmat

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
        minzeros=sys.maxsize
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
            
            for i in range(len(self._matrix)):
                for j in range(len(self._matrix[0])):
                    already_explored=False
                    # Already explored i
                    for sm in subm:
                        if i >= sm[1][0] and i <= sm[1][1] and \
                           j >= sm[0][0] and j <= sm[0][1]:
                            already_explored=True
                            break

                    if not already_explored and self._matrix[i][j] != 0:
                        # Void cell
                        v=h=0
                        min_v=float("inf")
                        min_h=float("inf")
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

#            i = 0
#            maxii = 0
#            while i < len(self._matrix):
#                j = 0
#                while j < len(self._matrix[i]):
#                    if self._matrix[i][j] == 0: j+=1; continue
#                    ii = i
#                    while ii < len(self._matrix) and self._matrix[ii][j] != 0:
#                        ii += 1
#                    if ii > maxii: maxii = ii 
#
#                    jj = j
#                    while jj < len(self._matrix[i]) and self._matrix[i][jj] != 0:
#                        jj += 1
#
#                    subm.append([(j,jj-1),(i,ii-1)])
#                    j = jj
#                i = maxii
#
            self.__look_for_superloop(subm)

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
            else:
                return subm

    # TODO: Think about complex cases with conditionals...

    def __look_for_superloop(self, subm):
        #def __sort_subm(a,b):
        #    if a[0][0] > b[0][0]:
        #        return 1
        #    else:
        #        return -1

        def __sort_subm(a):
            return a[0][0]

        def __map_subm(a):
            return (a[0][1]-a[0][0]+1, a[1][0])

        ssubm = sorted(subm, key=__sort_subm)
        ssubm = list(map(__map_subm, ssubm))

        # Looking for the minimum expression
        split_by = 1
        done = False
        while not done and split_by < len(ssubm):
            res = []
            done = True
            for i in range(0,len(ssubm), split_by):
                res.append(ssubm[i:i+split_by])

            prev = res[0]
            for r in res[1:]:
                done &= (r[0]==prev[0] and r[1]==prev[1])
                if not done:
                    break
                prev=r
            if done:
                break
            else:
                split_by += 1

        if done:
            min_times = len(res)
            min_ssubm = res[0]
            self._hidden_superloop = True
            self._hidden_superloop_its = min_times
