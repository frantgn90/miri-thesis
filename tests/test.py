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


import sys,numpy


def __submatrix(mat):
    subm=[]

    min_v=float("inf")
    min_h=float("inf")

    for i in range(len(mat)):
        for j in range(len(mat[0])):
            
            already_explored=False
            # Already explored i
            for sm in subm:
                if i > sm[1][0] and i < sm[1][1]:
                    already_explored=True
                    break
            # Already explored j
            for sm in subm:
                if j > sm[0][0] and j < sm[0][1]:
                    already_explored=True
                    break

            if not already_explored and mat[i][j] != 0: # Void cell
                v=h=0

                # Horitzontal min
                for ii in range(i, len(mat)):
                    if mat[ii][j] == 0: break
                    for jj in range(j, len(mat[0])):
                        if mat[ii][jj] != 0:
                            h+=1
                        else: break
                    if h < min_h: min_h=h

                # Vertical min
                for jj in range(j,len(mat[0])):
                    if mat[i][jj] == 0: break;
                    for ii in range(i, len(mat)):
                        if mat[ii][jj] != 0:
                            v+=1
                        else: break
                    if v < min_v: min_v=v
                subm.append([(j,j+min_h),(i,i+min_v)])

    # If all partitions are completelly disyunctive and can explain all 
    # the matrix, it means that every partition is a loop
    # TODO: Think about complex cases with conditionals...
    

    disyunctive=True

    visited_rows=[]
    visited_cols=[]

    # Let's test the rows
    for s in subm:
        rows_range=s[0]
        for i in range(rows_range[0], rows_range[1]):
            if not i in visited_rows:
                visited_rows.append(i)
            else:
                disyunctive=False
                break

    if disyunctive:
        # Let's test the cols
        for s in subm:
            cols_range=s[1]
            for i in range(cols_range[0], cols_range[1]):
                if not i in visited_cols:
                    visited_cols.append(i)
                else:
                    disyunctive=False
                    break

    if len(visited_rows)==len(mat[0]) and \
            len(visited_cols)==len(mat):
                completed=True
    else:
        completed=False


    print str(completed) + " " + str(disyunctive)
    if completed and disyunctive:
        # The partitioned matrixes have to be returned
        res=[]
        
        for s in subm:
            pmat=[]
            for i in range(s[1][0], s[1][1]):
                pmat.append(mat[i][s[0][0]:(s[0][1])])
            
            res.append(pmat)

    else:
        res=mat

    return res


def main(argc, argv):
    a=[[0,0,9,10],[0,0,11,12],[3,4,0,0]]
    a=[[1,30,33],[2,31,34],[3,32,35],[4,7,8]]
    a=[[1,2],[3,4]]
    
    subm=__submatrix(a)

    print str(subm)
    print
    print str(a)

    return 0




if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
