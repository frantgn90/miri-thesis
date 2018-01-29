#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, multiprocessing
import numpy as np

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.image import AxesImage

from sklearn.cluster import DBSCAN

from cluster import cluster
from utilities import pretty_print
import constants
import logging

"""
This is a customized matplotlib scale.
Maps to a cubic scale
"""

from matplotlib import scale as mscale
from matplotlib import transforms as mtransforms
import matplotlib.colors as colors


def plot_data(data):
    fig=plt.figure()
    #ax2d=fig.add_subplot(111)
    ax3d=fig.add_subplot(111,projection="3d")

    xs=[];ys=[];zs=[]
    for point in data:
            xs.append(point[0])
            ys.append(point[1])
            zs.append(point[2])
    #ax2d.scatter(xs,ys)
    ax3d.scatter(xs,ys,zs)
    
    #ax2d.set_xlabel(constants._x_axis)
    #ax2d.set_ylabel(constants._y_axis)

    ax3d.set_xlabel(constants._x_axis)
    ax3d.set_ylabel(constants._y_axis)
    ax3d.set_zlabel(constants._z_axis)
    
    #ax3d.set_xlim([-0.1,1.1])
    #ax3d.set_ylim([-0.1,1.1])
    #ax3d.set_zlim([-0.1,1.1])

    plt.show()

def normalize_data(data):
    data=np.array(data)
    amax=1/(np.amax(data,axis=0).transpose())
    data=data*amax

    return data

def multi_normalize_data(data_set):
    new_data_set = []
    for data in data_set:
        new_data_set.append(np.array(data))

    multi_amax=0
    for new_data in new_data_set:
        local_max=1/(np.amax(new_data,axis=0).transpose())
        if local_max > multi_amax:
            multi_amax=local_max

    for i in range(len(new_data_set)):
        new_data_set[i]=new_data_set[i]*multi_amax

    return new_data_set
 

def show_clustering(data, cdist, labels, core_samples_mask, n_clusters_, 
        total_time, deltas, bound):    
    X=np.array(data)
    
    fig, ax = plt.subplots()
    def onpick1(event):
        if isinstance(event.artist, Line2D):
            thisline = event.artist
            xdata = thisline.get_xdata()
            ydata = thisline.get_ydata()

            ind = event.ind

            points_info = ""
            for i in ind:
                xd = xdata[i]
                yd = ydata[i]

                for cs in cdist:
                    if cs.repetitions[cs.rank] == xd and cs.instants_distances_mean == yd:
                        points_info += str(cs)+"\n"
            print(pretty_print(points_info, "Points info"))

    unique_labels = set(labels)
    #colors = cm.Spectral(np.linspace(0, 1, len(unique_labels)))
    colors = ['b','g','r','c','m','y','k']

    while len(colors) < len(unique_labels):
        logging.warn("Some colors will be repeated in the plot")
        colors += colors 
    labels_colors = zip(unique_labels, colors)
    plt_labels=[]

    ''' Print clusters '''
    for k, col in labels_colors:
        if k == -1: col = 'k'

        class_member_mask = (labels == k)
        xy = X[class_member_mask & core_samples_mask]
        nxy = X[class_member_mask & ~core_samples_mask]

        lab,=ax.plot(xy[:, 0], xy[:, 1], marker='x', 
                markerfacecolor=col,markeredgecolor=col, markersize=10, 
                label="Cluster {0}".format(k),picker=5)

        plt_labels.append(lab)
        
        lab,=ax.plot(nxy[:, 0], nxy[:, 1], 'o', markerfacecolor=col,
                markeredgecolor=col, markersize=10, marker='o', linestyle='')
    
    ''' Show delta functions '''   
    periods = X[:, 1]
    periods.sort()

    inter_arrival = np.array(range(int(min(periods)),int(max(periods)),
                int((max(periods)-min(periods))/50)))

    for delta, col in zip(deltas,colors[::-1]): # Functions to be shown
        lab,=ax.plot(((delta*total_time)/inter_arrival),inter_arrival, 
                color=col, linestyle="--", label="delta={0}".format(delta))
        plt_labels.append(lab)

    #occurrences = X[:, 0]
    #occurrences.sort()
    #
    ## Upper boundary
    #occ_points = np.array(\
    #        range(\
    #            int(min(occurrences)),\
    #            int(max(occurrences)),\
    #            int((max(occurrences)-min(occurrences))/50)))
    #ax.plot(occ_points, (total_time/occ_points),"k--", color="blue", lw=1)
    #
    ## Bottom boundary
    #ax.plot(occ_points,(bound*total_time)/occ_points, "k--", color="red", lw=1) 
    #
    #ax.set_title("Number of clusters: {0} (eps={1}, mins={2})"
    #        .format(n_clusters_, 
    #        constants._eps, 
    #        constants._min_samples))
    
    
    ''' Show plot '''
    plt.xlabel(constants._x_axis_label)
    plt.ylabel(constants._y_axis_label)
    plt.legend(handles=plt_labels)
    #plt.gca().set_yscale("linear") #cubic
    
    plt.ylim([-0.1,np.max(X[:,1])])
    plt.xlim([-0.1,np.max(X[:,0])])

    plt.axhline(0, color='black')
    plt.axvline(0, color='black')

    fig.canvas.mpl_connect('pick_event', onpick1)

    plt.grid(True)
    plt.show()

def clustering(fcallstacks_pool, show_plot, total_time, delta, bound):
    import math
    
    ''' 1. Preparing data '''
    data=[]
    for cs in fcallstacks_pool:
        data.append([cs.repetitions[cs.rank], cs.instants_distances_mean,
            cs.burst_metrics[cs.rank]["42000050"]/cs.burst_metrics[cs.rank]["42000059"]])

    normdata=normalize_data(data)

    plot_data(normdata)
    
    ''' 2. Perform clustering '''
    db = DBSCAN(eps=constants._eps, min_samples=constants._min_samples).fit(normdata)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels=db.labels_

    ''' 3. Creating cluster objects '''
    nclusters = len(set(labels)) - (1 if -1 in labels else 0)
    clusters_pool=[]
    for i in range(0, nclusters):
        clusters_pool.append(cluster(i))
                
    assert len(labels) == len(fcallstacks_pool)
    for i in range(0,len(labels)):
        callstack_cluster_id=labels[i]
        fcallstacks_pool[i].cluster_id=callstack_cluster_id
        clusters_pool[callstack_cluster_id].add_callstack(fcallstacks_pool[i])

    ''' 4. Show plots '''
    #if show_plot:
    show_plot_thread=multiprocessing.Process(
            target=show_clustering,
            args=(data, fcallstacks_pool, labels, core_samples_mask, nclusters, 
                total_time, delta, bound))
    #show_plot_thread.start()

    return clusters_pool, show_plot_thread
