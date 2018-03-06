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
    def set_hwc_init(self, name, value):
        assert not name in self.hwc
        self.hwc[name] = value
    def set_hwc_fini(self, name, value):
        # Some HWC does not appear at the iterations entry
        # but only in the end. Why??
        #assert name in self.hwc
        #self.hwc[name] = value-self.hwc[name]
        # Extrae does the substraction from the last hwc evet 
        # for you. To be sure the numbers are correct just
        # be sure MPI HWC are deactivated.
        self.hwc[name] = value
    def calcule(self):
        pass

class loop(object):
    def __init__(self, loopid):
        self.loopid = loopid
        self.iterations = []
    def new_iteration(self, it):
        self.iterations.append(it)
    def set_init(self, init):
        self.init = init
    def set_fini(self, fini):
        assert fini > self.init
        self.fini = fini
        self.duration = self.fini - self.init
    def set_niters(self, niters):
        self.niters = niters
        self.chance = len(self.iterations) / niters
    def calcule(self):
        import numpy as np
        self.ittime_mean = np.mean(list(map(
            lambda x: x.duration, self.iterations)))
        self.ittime_median = np.median(list(map(
            lambda x: x.duration, self.iterations)))
        self.ittime_std = np.std(list(map(
            lambda x: x.duration, self.iterations)))
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
                lambda x: x.hwc[hwc_key], self.iterations)))
            self.hwc_median[hwc_key] = np.median(list(map(
                lambda x: x.hwc[hwc_key], self.iterations)))
            self.hwc_std[hwc_key] = np.std(list(map(
                lambda x: x.hwc[hwc_key], self.iterations)))

loop_stack = stack()
iter_stack = stack()
loop_hmap  = {}

def loop_handler(loop_record):
    if loop_record.entry:
        loopobj = loop(loop_record.loopid)
        loopobj.set_init(loop_record.time)
        loop_stack.push(loopobj)
    elif loop_record.exit:
        loopobj = loop_stack.pop()
        loopobj.set_fini(loop_record.time)
        # A sublop will be repetaed as many times as iterations
        # have the superloop so put all them together.
        if loopobj.loopid in loop_hmap:
            loop_hmap[loopobj.loopid].append(loopobj)
        else:
            loop_hmap[loopobj.loopid] = [loopobj]


def iter_handler(iter_record, hwc_record_set):
    if iter_record.entry:
        itobj = iteration(iter_record.iterid)
        itobj.set_init(iter_record.time)
        for hwc_record in hwc_record_set:
            itobj.set_hwc_init(hwc_record.type_name_short, hwc_record.value)
        iter_stack.push(itobj)
    elif iter_record.exit:
        itobj = iter_stack.pop()
        itobj.set_fini(iter_record.time)
        for hwc_record in hwc_record_set:
            itobj.set_hwc_fini(hwc_record.type_name_short, hwc_record.value)
        loop_stack.top().new_iteration(itobj)

def niter_handler(niter_record):
    loop_stack.top().set_niters(niter_record.niters)

def main(argc, argv):
    tracefile = argv[1]
    parser = trace(tracefile)

    def event_handler(record):
        # Just for testing purposes!
        if record.task_id == 1:
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

    parser.parse(event_callback=event_handler)

    for loopid, loopset in loop_hmap.items():
        for loopobj in loopset:
            loopobj.calcule()
            print("--- {0} ---".format(loopobj.loopid))
            print("It. Chance  = {0}".format(loopobj.chance))
            print("N.Its   = {0}".format(loopobj.niters))
            print("It.mean = {0}".format(loopobj.ittime_mean))
            print("It.medi = {0}".format(loopobj.ittime_median))
            print("It.std  = {0}".format(loopobj.ittime_std))
            print("--- HWC ---")
            for name in loopobj.hwc_keys:
                print("{0:>20} = {1}".format(name+"   Mean",
                    round(loopobj.hwc_mean[name],2)))
                print("{0:>20} = {1}".format(name+" Median",
                    round(loopobj.hwc_median[name],2)))
                print("{0:>20} = {1}".format(name+"    Std",
                    round(loopobj.hwc_std[name],2)))
                


if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
