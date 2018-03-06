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

class loop(object):
    def __init__(self, loopid):
        self.loopid = loopid

    def new_iteration(self, it):
        self.iterations.append(it)

loop_stack = stack()
loop_hmap  = {}

def loop_handler(loop_events):
    assert len(loop_events) == 0
    l = loop_events[0]
    if l.entry:
        if not l.loopid in loop_hmap:
            loop_hmap[l.loopid] = loop(l.loopid)
        loop_stack.push(loop_hmap[l.loopid])
    elif l.exit:
        loop_stack.pop()

def iter_handler(iter_events):
    assert len(niter_events) == 0
    pass

def niter_handler(niter_events):
    assert len(niter_events) == 0


def main(argc, argv):
    tracefile = argv[1]
    parser = trace(tracefile)

    def event_handler(record):
        if record.task_id == 1:
            if len(record.events["LOOP"]) > 0:
                loop_handler(record.events["LOOP"])
            if len(record.events["ITER"]) > 0:
                iter_handler(record.events["ITER"])
            if len(record.events["NITER"]) > 0:
                niter_handler(record.events["NITER"])

    parser.parse(event_callback=event_handler)

if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
