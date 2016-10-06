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

import sys, os
import numpy

from traceParsing import *
from callstackDistribution import *
from calculateDelta import *
from clustering import *

import constants


_empty_cell=0


def print_matrix(matrix, infile):
    if type(matrix)==list:
        mat=matrix
    else:
        mat=matrix.tolist()

    def format_nums(val):
        return str(val).zfill(2)

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

    if minzeros > 0:
        for row in mat:
            del row[-minzeros:]

    return mat


def filter_cluster(rank, cluster):
    keys_cs=[]
    index=0
    max_size=0

    tomat=[]

    for cs in cluster:
        k=cs.keys()[0]
        
        if int(cs[k]["rank"]) != rank: continue

        if len(cs[k]["when"]) > max_size:
            max_size=len(cs[k]["when"]) 
            for i in range(index-1, -1, -1):
                holes=max_size-len(tomat[i])
                tomat[i].extend([_empty_cell]*holes)
        elif len(cs[k]["when"]) < max_size:
            holes=max_size-len(cs[k]["when"])
            cs[k]["when"].extend([_empty_cell]*holes)

        tomat.append(cs[k]["when"])
        keys_cs.append(k)
        index+=1

    return numpy.matrix(tomat),max_size

def calculate_it_boundaries(cluster):
    # For the moment, only for rank 0
    tmat,max_size=filter_cluster(0, cluster)

    # For the moment w/o references to the callstacks
    '''
    ki=0
    for row in tomat:
        row.append(ki)
        ki+=1
    '''

    # Sorting by the first column
    tmat=tmat.view("i8,"*(max_size-1)+"i8")
    tmat.sort(order=["f0"], axis=0)
    tmat=tmat.view(np.int)

    keys_ordered=[]
    '''
    ordered_calls=tmat[:,max_size].transpose()

    # Get the calls ordered by times
    for row in range(len(keys_cs)):
        ki=tmat.item((row,-1))
        keys_ordered.append(keys_cs[ki])
    '''

    # Adding holes if needed
    tmat=boundaries_sort_2(tmat)

    iterations=[]
    mheight=len(tmat)
    mwidth=len(tmat[0])
  
    print_matrix(tmat, True)
    # It is defined by the row. Remember that every tow corresponds to a different call
    last_call=0; ini_it=tmat[0][0]

    for j in range(mwidth):
        for i in range(mheight):
            if tmat[i][j]==0:continue
            if i==last_call and j!=0:
                fin_it=tmat[i][j]
                iterations.append((ini_it,fin_it))
                ini_it=fin_it
                last_call=i

    return iterations, keys_ordered
    #return tmat.tolist()[0][:-1], keys_ordered 

def main(argc, argv):
    if argc < 2:
        print("Usage(): {0} [-l call_level] [-f img1[,img2,...]] <trace>\n"
                .format(argv[0]))
        return -1

    level="0"; trace = argv[-1]; image_filter=["ALL"]
    for i in range(1, len(argv)-1):
        if argv[i] == "-f": image_filter=argv[i+1].split(",")
        elif argv[i] == "-l": level=argv[i+1]

    clevels = "All"
    if level != "0":
        clevels=str(level)

    if constants._verbose:
        print("{0} : Calls level={1}; Image filter={2}; Trace={3}\n\n"
                .format(argv[0], clevels, str(image_filter), trace.split("/")[-1]))

    cs_files,app_time=get_callstacks(trace, level, image_filter)

    if constants._verbose: print("[Merging data]")

    mean_delta=0; filtered_data=[]; nonfiltered_data=[]
    for csf in cs_files:
        cdist=getCsDistributions(csf)
        new_delta, new_fdata=getDelta(cdist,app_time)
        mean_delta+=new_delta
        filtered_data.append(new_fdata)
        nonfiltered_data.append(cdist)

    mean_delta/=len(cs_files)
    nclusters, clustered_data=clustering(filtered_data, True)

    # Printing results
    ordered_cluster={}
    for cluster in clustered_data.keys():
        it_cluster,cs_ordered=calculate_it_boundaries(clustered_data[cluster])

        print("Cluster {0} have been found {1} iterations]"
                .format(cluster, len(it_cluster)))
        cnt=1
        print("> Iteration_TOT  found @ [ {0} , {1} )"
                .format(it_cluster[0][0], it_cluster[-1][1]))
    
        
        if len(it_cluster) < 50:
            for i in range(len(it_cluster)):
                print(" - Iteration_{0} found @ [ {1} , {2} )"
                        .format(cnt,it_cluster[i][0],it_cluster[i][1]))
                cnt+=1
        

        '''
        print("[Every iteration has this calls]")
        for cs in cs_ordered:
            print("-  {0}".format(cs))
        '''
        
    print("[Results]")
    print("  -> {0} clusters detected".format(nclusters))
    print("  -> Really useful time (in loops): {0:.2f} %".format(mean_delta*100))
    print("[Done]")

    # Remove all temporal files
    for csf in cs_files: os.remove(csf)

    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
