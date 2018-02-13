#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright © 2018 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>

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
import subprocess
import tempfile
import os
import logging
import numpy
import csv
import matplotlib.pyplot as plt
import random
import math

colors = ['b','g','r','c','m','y','k']

def plot(results,nloops):
    # For the moment just one result

    ncols = 3
    nrows = math.ceil(len(results)/float(ncols))

    fig = plt.figure()
    subplots = []
    for i in range(len(results)):
        subplots.append(fig.add_subplot(ncols*100+nrows*10+i+1))

    for ki,key in enumerate(results):
        result = results[key]

        keys = sorted(result)
        values = []
        for k in keys:
            values.append(result[k])

        tickspos = []
        for i in range(nloops):
            ri = list(range(i,len(result),nloops))
            bi = values[i*nloops:(i*nloops)+nloops]
            tickspos.extend(ri)

            subplots[ki].bar(ri, bi, width = 0.9, color = colors[i], 
                    label="Loop {0}".format(i), align='center', linewidth=0)

        subplots[ki].legend()
        subplots[ki].set_title(key)

        #ticks = list(map(lambda x: x.split("_")[-1],keys))
        #subplots[i].xticks(tickspos, ticks, rotation=90)
        #subplots[i].subplots_adjust(bottom= 0.2, top = 0.90)

    plt.show()

def histogram_parser(hfile):

    # Split into planes

    planes_files = []
    planes_ids = []
    logging.debug("Processing file:{0}".format(hfile.name))
    for line in hfile:
        if line == "": continue
        if "---" in line: # Little modification on paramedir.
            planes_ids.append(line[3:].replace("\n", ""))
            planes_files.append(tempfile.NamedTemporaryFile(mode="r+",
                    prefix="paramedir_plane_{0}_".format(planes_ids[-1])))
            continue
        else:
            planes_files[-1].write(line)

    for ff in planes_files:
        ff.seek(0,0)

    logging.debug("Planes tempfiles={0}".format(
        list(map(lambda x:x.name,planes_files))))
    parsed_planes = list(map(
        lambda x: csv.reader(x, delimiter="\t"),
        planes_files))

    #for pf in planes_files:
    #    pf.close()

    planes_histograms = list(zip(planes_ids,parsed_planes))

    loops_info = dict.fromkeys(planes_ids)
    for key in loops_info:
        loops_info[key]={}

    for lid, plane in planes_histograms:
        header = True
        for row in plane:
            if header: header=False;continue
            if len(row) == 0: continue
            rowname = row[0]
            rowvalues = row[1:-1]
            rownumbers = list(map(lambda x: float(x), rowvalues))
            loops_info[lid].update({rowname+"_mean":numpy.mean(rownumbers)})
    
    return loops_info

def main(argc, argv):
    trace = argv[1]
    trace = os.path.abspath(trace)

    cfgs_in = argv[2]
    cfgs_in = os.path.abspath(cfgs_in)

    CFGS = []
    with open(cfgs_in) as cfgs_fd:
        for line in cfgs_fd:
            line = line.replace("\n","")
            if line[:2] == "//": continue 
            if len(line) == 0 : continue 
            CFGS.append(line)

    #Level      Numeric value
    #------------------------
    #CRITICAL  |  50
    #ERROR     |  40
    #WARNING   |  30
    #INFO      |  20
    #DEBUG     |  10
    #NOTSET    |  0

    logging.basicConfig(level=20)
    command = ["paramedir", trace]
    
    temporal_outfiles = []
    for cfg in CFGS:
        short_name = cfg.split("/")[-1]
        temporal_outfiles.append((short_name, tempfile.NamedTemporaryFile(mode="r", 
            prefix="paramedir_temp_out")))
        logging.debug("[{0}]Temporal out={1}".format(short_name, 
            temporal_outfiles[-1][1].name))

        command.extend([cfg,temporal_outfiles[-1][1].name])

    child = subprocess.Popen(command)
    return_code = child.wait()

    logging.debug("Return code={0}".format(return_code))

    histograms = []
    for outfile in temporal_outfiles:
        histograms.append(histogram_parser(outfile[1]))
        histograms[-1].update({"cfg_name":outfile[0]})


    # All cfgs must be 3D where 3th dimension is the loop-id, so
    # same number of planes for all histograms.
    nloops = len(histograms[0])-1
    logging.info("N.Loops={0}".format(nloops)) # "cfg_name" must not be counted

    result = {}
    for histogram in histograms:
        assert len(histogram) == nloops+1
        cfg_name = histogram["cfg_name"]
        result.update({cfg_name:{}})

        for plane in histogram:
            if plane == "cfg_name":continue
            planename = plane.replace(" ","_")
            result[cfg_name].update(
                {planename+"_total":round(histogram[plane]["Total_mean"],2)})
            result[cfg_name].update(
                {planename+"_average":round(histogram[plane]["Average_mean"],2)})
            result[cfg_name].update(
                {planename+"_stdev":round(histogram[plane]["Stdev_mean"],2)})

    for outfile in temporal_outfiles:
        outfile[1].close()
    
    plot (result,nloops)
    logging.info("Bye!")


if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
