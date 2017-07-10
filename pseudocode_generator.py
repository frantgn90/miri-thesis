#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, logging
import numpy as np

import constants, logging
from cluster import cluster

def merge_clusters(clusters_pool):
    logging.info("Classifying clusters by delta.")

    cluster_by_delta = {}
    def ___cluster_classification(x):
        delta = x.delta
        if delta in cluster_by_delta: 
            cluster_by_delta[delta].append(x)
        else: 
            cluster_by_delta[delta]=[x]

    map(___cluster_classification, clusters_pool)

    for k,v in cluster_by_delta.items():
        logging.debug("Sorting clusters ({0}) with delta={1}".format(len(v), k))
        v.sort(key=lambda x: x.get_interarrival_median(), reverse=False)

    # Then, the merge must be done from the little one to the biggest one.
    top_level_clusters=[]
    for delta,clusters in cluster_by_delta.items():
        logging.info("Merging {0} clusters with delta={1}".format(len(clusters),delta))
        for i in range(len(clusters)-1):
            done=False
            for j in range(i+1,len(clusters)):
                logging.info("Cluster {0} merged to {1}?"\
                        .format(clusters[i].cluster_id, clusters[j].cluster_id))
                if clusters[j].get_interarrival_median() >\
                        clusters[i].get_interarrival_median()\
                        and clusters[j].is_subloop(clusters[i]):

                    logging.info("Cluster {0} ({1}) merged to {2} ({3})".
                        format(clusters[i].cluster_id, clusters[i].get_interarrival_median(),
                               clusters[j].cluster_id, clusters[j].get_interarrival_median()))

                    clusters[j].merge(clusters[i])
                    done=True
                    break

                logging.info("... No, there is no a subloop")

            assert done, "Error at cluster level merge"
        top_level_clusters.append(cluster_by_delta[delta][-1])

    return top_level_clusters
