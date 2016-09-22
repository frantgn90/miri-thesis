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
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

import numpy as np
from sklearn.cluster import DBSCAN

_x_axis_label="Number of occurrences"
_y_axis_label="Mean period bw occurrences"

_x_axis="times"
_y_axis="time_mean"
_z_axis="time_std"

_eps=0.01
_min_samples=5

def plot_data(cdist):
    fig=plt.figure()
    ax2d=fig.add_subplot(111)
    #ax3d=fig.add_subplot(111,projection="3d")

    xs=[];ys=[];zs=[]
    for cs in cdist:
        for k,v in cs.items():
            xs.append(v[_x_axis])
            ys.append(v[_y_axis])
            zs.append(v[_z_axis])
    ax2d.scatter(xs,ys)
    #ax3d.scatter(xs,ys,zs)
    
    ax2d.set_xlabel(_x_axis)
    ax2d.set_ylabel(_y_axis)

    #ax3d.set_xlabel(_x_axis)
    #ax3d.set_ylabel(_y_axis)
    #ax3d.set_zlabel(_z_axis)

    plt.show()


def normalize_data(data):
    data=np.array(data)
    amax=1/(np.amax(data, axis=0).transpose())
    data=data*amax

    return data

def clustering(cdist):
    # Preparing data
    data=[]
    for cs in cdist:
        for k,v in cs.items():
            data.append([v[_x_axis],v[_y_axis]])

    data=normalize_data(data)

    # Perform clustering
    db = DBSCAN(eps=_eps, min_samples=_min_samples).fit(data)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels=db.labels_

    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

    # Show clustering plot
    X=np.array(data)
    unique_labels = set(labels)
    colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # Black used for noise.
            col = 'k'

        class_member_mask = (labels == k)

        xy = X[class_member_mask & core_samples_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
                 markeredgecolor=col, markersize=9, marker='x')

        xy = X[class_member_mask & ~core_samples_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col,
                 markeredgecolor=col, markersize=9, marker='x')

    plt.title('Estimated number of clusters: %d' % n_clusters_)
    plt.xlabel(_x_axis_label)
    plt.ylabel(_y_axis_label)
    plt.show()

    return n_clusters_
