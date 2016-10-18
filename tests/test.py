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
from struct_detection import *

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


def testing(mat):
    mheight=len(mat)
    mwidth=len(mat[0])

    last=mat[0][0]
    lastcol=0
    lastrow=0

    i=0
    #for i in range(mwidth):
    while i < len(mat[0]):
        for j in range(mheight):
            if mat[j][i]==0: continue
            if mat[j][i] < last:
                
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

    for row in mat:
        del row[-minzeros:]


def main(argc, argv):
    a=[[1,6,9,10],[2,7,11,12],[3,4,5,13]]
    #a=[[1,30,33],[2,31,34],[3,32,35],[4,7,8]]
    #a=[[1,2],[3,4]]
    
    testing(a)
    print_matrix(a,False)

    return 0




if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
