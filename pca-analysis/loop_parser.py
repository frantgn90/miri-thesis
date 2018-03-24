#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright © 2018 Juan Francisco Martínez Vera <juan.martinez[AT]bsc.es>

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
from trace import trace
#from trace_mp import trace_mp
import numpy as np
from collections import defaultdict

class mergebykey(object):
    def __init__(self, listofdicts):
        self.res = defaultdict(list)
        for d in listofdicts:
            for key,val in d.items():
                self.res[key].append(val)
    def __iter__(self):
        return iter(self.res.items())

class stack(object):
    def __init__(self):
        self.stack = []
    def push(self, v):
        self.stack.append(v)
    def top(self):
        return self.stack[-1]
    def pop(self):
        return self.stack.pop()

class iteration(object):
    def __init__(self, iterid):
        self.iterid = iterid
        self.hwc = {}
    def set_init(self, init):
        self.init = init
    def set_fini(self, fini):
        assert fini > self.init
        self.fini = fini
        self.duration = self.fini - self.init
    #def set_hwc_init(self, name, value):
    #    assert not name in self.hwc
    #    self.hwc[name] = value
    def set_hwc_fini(self, name, value):
        # Some HWC does not appear at the iterations entry
        # but only in the end. Why??
        #assert name in self.hwc
        self.hwc[name] = value
    def calcule(self):
        pass

class loop(object):
    def __init__(self, loopid, code_loc):
        self.loopid = loopid
        self.iterations = []
        # One loop can be executed so many times
        # if it is a subloop
        self.init=[]
        self.fini=[]
        self.duration=[]
        self.niters=[]
        self.code_loc = code_loc
        self.total_iters=0
    def new_iteration(self, it):
        self.iterations.append(it)
    def set_init(self, init):
        self.init.append(init)
    def set_fini(self, fini):
        assert fini > self.init[-1]
        self.fini.append(fini)
        self.duration.append(self.fini[-1] - self.init[-1])
    def set_niters(self, niters):
        self.niters.append(niters)
    def get_total_iters(self):
        return sum(self.niters)
    def calcule(self):
        if self.get_total_iters() > 0:
            self.chance = len(self.iterations) / self.get_total_iters()
        else:
            self.chance = 0

        self.ittime_mean = np.mean(list(map(
            lambda x: x.duration, self.iterations)))
        self.ittime_median = np.median(list(map(
            lambda x: x.duration, self.iterations)))
        self.ittime_std = np.std(list(map(
            lambda x: x.duration, self.iterations)))
        self.niters_mean = np.mean(self.niters)
        self.niters_median = np.median(self.niters)
        self.niters_std = np.std(self.niters)
        hwc_keys = list(map(lambda x: list(x.hwc.keys()), self.iterations))
        self.hwc_keys=[]
        for k in hwc_keys: self.hwc_keys.extend(k)
        self.hwc_keys = sorted(list(set(self.hwc_keys)))
        self.hwc_mean = dict.fromkeys(self.hwc_keys)
        self.hwc_median = dict.fromkeys(self.hwc_keys)
        self.hwc_std = dict.fromkeys(self.hwc_keys)
        # Lets assume just one HWC set
        for hwc_key in self.hwc_keys:
            self.hwc_mean[hwc_key] = np.mean(list(map(
                lambda x: x.hwc[hwc_key] if hwc_key in x.hwc else 0 , 
                self.iterations)))
            self.hwc_median[hwc_key] = np.median(list(map(
                lambda x: x.hwc[hwc_key] if hwc_key in x.hwc else 0, 
                self.iterations)))
            self.hwc_std[hwc_key] = np.std(list(map(
                lambda x: x.hwc[hwc_key] if hwc_key in x.hwc else 0, 
                self.iterations)))

loop_stack = [] #stack()
iter_stack = [] #stack()
loop_hmap  = [] #{}

def loop_handler(loop_record):
    if loop_record.entry:
        if loop_record.loopid in loop_hmap[loop_record.task_id-1]:
            loopobj = loop_hmap[loop_record.task_id-1][loop_record.loopid]
        else:
            loopobj = loop(loop_record.loopid, loop_record.loop_name)
        loopobj.set_init(loop_record.time)
        loop_stack[loop_record.task_id-1].push(loopobj)
    elif loop_record.exit:
        loopobj = loop_stack[loop_record.task_id-1].pop()
        loopobj.set_fini(loop_record.time)
        if not loopobj.loopid in loop_hmap[loop_record.task_id-1]:
            loop_hmap[loop_record.task_id-1][loopobj.loopid] = loopobj


def iter_handler(iter_record, hwc_record_set):
    if iter_record.entry:
        itobj = iteration(iter_record.iterid)
        itobj.set_init(iter_record.time)
        # Extrae reset HWC once they are gathered so
        # substraction is not needed.
        #for hwc_record in hwc_record_set:
        #    itobj.set_hwc_init(hwc_record.type_name_short, hwc_record.value)
        iter_stack[iter_record.task_id-1].push(itobj)
    elif iter_record.exit:
        itobj = iter_stack[iter_record.task_id-1].pop()
        itobj.set_fini(iter_record.time)
        for hwc_record in hwc_record_set:
            itobj.set_hwc_fini(hwc_record.type_name_short, hwc_record.value)
        loop_stack[iter_record.task_id-1].top().new_iteration(itobj)

def niter_handler(niter_record):
    loop_stack[niter_record.task_id-1].top().set_niters(niter_record.niters)

def mergeloops(loops):
    assert len(set(map(lambda x: x.loopid,loops))) == 1
    if len(loops) == 1:
        return loops[0]

    new_loop = loop(loops[0].loopid, loops[0].code_loc)
    new_loop.total_iters = np.mean(list(map(lambda x: x.get_total_iters(),loops)))
    new_loop.chance = np.mean(list(map(lambda x: x.chance,loops)))
    new_loop.ittime_mean = np.mean(list(map(lambda x: x.ittime_mean,loops)))
    new_loop.ittime_median = np.mean(list(map(lambda x: x.ittime_median,loops)))
    new_loop.ittime_std = np.mean(list(map(lambda x: x.ittime_std,loops)))
    new_loop.niters_mean = np.mean(list(map(lambda x: x.niters_mean,loops)))
    new_loop.niters_median = np.mean(list(map(lambda x: x.niters_median,loops)))
    new_loop.niters_std = np.mean(list(map(lambda x: x.niters_std,loops)))

    new_loop.hwc_keys = []
    for l in loops:
        new_loop.hwc_keys.extend(l.hwc_keys)
    new_loop.hwc_keys = sorted(list(set(new_loop.hwc_keys)))
    new_loop.hwc_mean = dict.fromkeys(new_loop.hwc_keys)
    new_loop.hwc_median = dict.fromkeys(new_loop.hwc_keys)
    new_loop.hwc_std = dict.fromkeys(new_loop.hwc_keys)
    for hwc_key in new_loop.hwc_keys:
        floops = filter(lambda x: hwc_key in x.hwc_keys, loops)
        new_loop.hwc_mean[hwc_key] = np.mean(list(
            map(lambda x: x.hwc_mean[hwc_key], floops)))
        new_loop.hwc_median[hwc_key] = np.mean(list(
            map(lambda x: x.hwc_median[hwc_key], floops)))
        new_loop.hwc_std[hwc_key] = np.mean(list(
            map(lambda x: x.hwc_std[hwc_key], floops)))
    return new_loop

def merge(loops_by_rank):
    res=dict()
    for key,loops in mergebykey(loops_by_rank):
        res[key]=mergeloops(loops)
    return res

def main(argc, argv):
    tracefile = argv[1]
    parser = trace(tracefile)

    def event_handler(record):
        # Is important to maintain the order of the
        # handlers calls since we are working with
        # stacks.
        if len(record.events["LOOP"]) > 0:
            assert len(record.events["LOOP"]) == 1
            loop_handler(record.events["LOOP"][0])
        # We are waiting for hwc to be injected at same record
        # as iter. Event_eventandcounters API call have been used.
        if len(record.events["ITER"]) > 0:
            assert len(record.events["ITER"]) == 1
            assert len(record.events["HWC"]) > 0
            iter_handler(record.events["ITER"][0],
                    record.events["HWC"])
        if len(record.events["NITER"]) > 0:
            assert len(record.events["NITER"]) == 1
            niter_handler(record.events["NITER"][0])

    for i in range(parser.get_ntasks()):
        loop_stack.append(stack())
        iter_stack.append(stack())
        loop_hmap.append(dict())

    parser.parse(event_callback=event_handler)

    for task in parser.get_taskids():
        for loopid, loopobj in loop_hmap[task].items():
            loopobj.calcule()
    
    import csv
    if (True):
        merged_loops=merge(loop_hmap)
        hwc_keys = set()
        for loopid, loopobj in merged_loops.items():
            hwc_keys.update(loopobj.hwc_keys)
        with open(tracefile.replace(".prv","_loops_merged.csv"), "w", 
                newline='')as csvfile:
            loopswriter = csv.writer(csvfile,quoting=csv.QUOTE_MINIMAL)
            loopswriter.writerow([
                "Loop loc.",
                "Total iters",
                #"Iters",
                #"Iters med", 
                #"Iters std", 
                "Iter time m", 
                #"Iter time med", 
                "Iter time std"] 
                + list(map(lambda x: x+"_mean", hwc_keys))
                #+ list(map(lambda x: x+"_median", task_hwc_keys))
                #+ list(map(lambda x: x+"_std", taskhwc_keys))
                )

            for loopid,loopobj in merged_loops.items():
                if loopobj.niters_mean <= 1: continue
                loopswriter.writerow(
                          [loopobj.code_loc]
                        + [loopobj.total_iters]
                #        + [loopobj.niters_mean]
                #        + [loopobj.niters_median]
                #        + [loopobj.niters_std]
                        + [loopobj.ittime_mean]
                #        + [loopobj.ittime_median]
                        + [loopobj.ittime_std]
                        + [ loopobj.hwc_mean[key] for key in hwc_keys 
                            if key in loopobj.hwc_mean]
                #       + [ loopobj.hwc_median[key] for key in hwc_keys ]
                #        + [ loopobj.hwc_std[key] for key in hwc_keys ]
                )


    else:
        for task in parser.get_taskids():
            task_hwc_keys = set()
            for loopid, loopobj in loop_hmap[task].items():
                task_hwc_keys.update(loopobj.hwc_keys)

            with open(tracefile.replace(".prv","_loops_{0}.csv"
                .format(task)), 
                    "w", newline='') as csvfile:
                loopswriter = csv.writer(csvfile,quoting=csv.QUOTE_MINIMAL)
                loopswriter.writerow([
                    "Loop loc.",
                    "Total iters",
                    #"Iters",
                    #"Iters med", 
                    #"Iters std", 
                    "Iter time m", 
                    #"Iter time med", 
                    "Iter time std"] 
                    + list(map(lambda x: x+"_mean", task_hwc_keys))
                    #+ list(map(lambda x: x+"_median", task_hwc_keys))
                    #+ list(map(lambda x: x+"_std", taskhwc_keys))
                    )

                for loopid,loopobj in loop_hmap[task].items():
                    if loopobj.niters_mean <= 1: continue
                    loopswriter.writerow(
                              [loopobj.code_loc]
                            + [loopobj.get_total_iters()]
                    #        + [loopobj.niters_mean]
                    #        + [loopobj.niters_median]
                    #        + [loopobj.niters_std]
                            + [loopobj.ittime_mean]
                    #        + [loopobj.ittime_median]
                            + [loopobj.ittime_std]
                            + [ loopobj.hwc_mean[key] for key in task_hwc_keys 
                                if key in loopobj.hwc_mean]
                    #       + [ loopobj.hwc_median[key] for key in task_hwc_keys ]
                    #        + [ loopobj.hwc_std[key] for key in task_hwc_keys ]
                    )


if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
