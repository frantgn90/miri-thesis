#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, logging
import numpy as np

import constants
from cluster import cluster

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


def get_random_iters(clusters, n_random_iterations):
    random_iters=[]

    for i in range(len(cluster_set)-1):
        random_iters.append(cluster_set[i+1].getRandomIterations(n_random_iterations))

    random_iters.append(cluster_set[-1].getRandomIterations(n_random_iterations))
    return random_iters

def merge_clusters(cluster_set, ranks):
    
    # Now, the clusters are sorted by number of occurrences
    # it means that the clusters that are first are the subloops ones
    # and those clusters that are at the end are the superloops ones.
    # (For now we are not taking into account the data conditionals)
    cluster_set.sort(key=lambda x: x.getOccurrences(), reverse=True)
    
    # Then, the merge must be done from the little one to the biggest one.
    for i in range(len(cluster_set)-1):

        done=False
        for j in range(i+1,len(cluster_set)):
            if cluster_set[j].getOccurrences() < cluster_set[i].getOccurrences():
                logging.debug("{0} occ. -> {1} occ.".format(
                    cluster_set[i].getOccurrences(),
                    cluster_set[j].getOccurrences()))
                
                cluster_set[j].merge(cluster_set[i])
                done=True

        assert done, "Error at cluster level merge"

    # Finally, the last one will have all the merged clusters
    return cluster_set[-1]
