#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, logging
import numpy as np

import constants, logging
from cluster import cluster

def get_random_iters(clusters, n_random_iterations):
    random_iters=[]

    for i in range(len(cluster_set)-1):
        random_iters.append(cluster_set[i+1].getRandomIterations(n_random_iterations))

    random_iters.append(cluster_set[-1].getRandomIterations(n_random_iterations))
    return random_iters

def merge_clusters(cluster_set, ranks):
 
    # clusters should be classified by delta. Every delta is an
    # entire big loop
    logging.info("Classifying clusters by delta.")

    cluster_by_delta = {}
    for cluster in cluster_set:
        delta = cluster._delta
        if delta in cluster_by_delta:
            cluster_by_delta[delta].append(cluster)
        else:
            cluster_by_delta.update({delta:[cluster]})

    # Now, the clusters are sorted by number of occurrences
    # it means that the clusters that are first are the subloops ones
    # and those clusters that are at the end are the superloops ones.
    # (For now we are not taking into account the data conditionals)

    for k,v in cluster_by_delta.items():
        logging.debug("Sorting clusters ({0}) with delta={1}".format(len(v), k))
        v.sort(key=lambda x: x.getOccurrences(), reverse=True)
    logging.debug("Clusters sorted for merging.")

    # Then, the merge must be done from the little one to the biggest one.
    top_level_clusters=[]

    for delta,clusters in cluster_by_delta.items():
        logging.info("Merging clusters with delta={0}".format(delta))

        for i in range(len(clusters)-1):
            done=False
            for j in range(i+1,len(clusters)):
                if clusters[j].getOccurrences() < clusters[i].getOccurrences():
                    logging.debug("Cluster {0} ({1}) merged with {2} ({3})".
                            format(i, clusters[i].getOccurrences(),
                                   j, clusters[j].getOccurrences()))
                    clusters[j].merge(clusters[i])
                    done=True
                    break

            assert done, "Error at cluster level merge"
        top_level_clusters.append(cluster_by_delta[delta][-1])

    # Finally, the last one will have all the merged clusters
    return top_level_clusters
