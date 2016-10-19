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

from loop import cluster

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


def generate_pseudocode(clusters, ranks):

    ocluster=[]
    # Assuming every cluster is a loop
    for k in clusters.keys():
        new_ocluster = cluster(clusters[k], ranks)
        ocluster.append(new_ocluster)


    # TODO: Clusters level merge
    for cl in ocluster:
        return cl.str()


