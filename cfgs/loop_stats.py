#! /usr/bin/env python
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

CFG_COUNTER = "/home/jmartinez/BSC/master/git/cfgs/3D_loop_counter.cfg"
CFG_IT_PROFILE = "/home/jmartinez/BSC/master/git/cfgs/3D_loop_profile.cfg"
CFG_PERIOD = "/home/jmartinez/BSC/master/git/cfgs/3D_loop_period.cfg"

def histogram_parser(hfile):

    # Split into planes

    planes_files = []
    planes_ids = []
    for line in hfile:
        if line == "": continue
        if "value" in line:
            planes_ids.append(line.replace("\n", ""))
            planes_files.append(tempfile.NamedTemporaryFile(mode="r+",
                    prefix="paramedir_plane_{0}_".format(planes_ids[-1])))
            continue
        else:
            planes_files[-1].write(line)

    for ff in planes_files:
        ff.seek(0,0)

    logging.info("Planes tempfiles={0}".format(
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

    counter_out = tempfile.NamedTemporaryFile(mode="r", prefix="paramedir_c")
    profile_out = tempfile.NamedTemporaryFile(mode="r", prefix="paramedir_p")
    period_out = tempfile.NamedTemporaryFile(mode="r", prefix="paramedir_p")

    logging.basicConfig(level=1)
    logging.info("Counter out={0}".format(counter_out.name))
    logging.info("Profile out={0}".format(profile_out.name))

    command = ["paramedir", trace, 
            CFG_COUNTER,    counter_out.name, 
            CFG_IT_PROFILE, profile_out.name,
            CFG_PERIOD,     period_out.name]
    child = subprocess.Popen(command)
    return_code = child.wait()

    logging.info("Return code={0}".format(return_code))

    counter_res = histogram_parser(counter_out)
    profile_res = histogram_parser(profile_out)
    period_res = histogram_parser(period_out)

    assert len(counter_res) == len(profile_res)
    assert len(counter_res) == len(period_res)

    # Different planes are different loops
    nloops = len(counter_res)
    logging.info("N.Loops={0}".format(nloops))

    for loop_info in counter_res:
        print ("{0}={1}".format(loop_info,
            counter_res[loop_info]["Total_mean"]))
    for loop_info in period_res:
        print ("{0}={1}".format(loop_info,
            round(period_res[loop_info]["Total_mean"],2)))

    counter_out.close()
    profile_out.close()
    logging.info("Bye!")


if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
