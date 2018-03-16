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

from trace import *
from callstack import call, callstack

class callstacks_parser(object):
    def __init__(self, tracefile):
        self._trace = trace(tracefile)
        self.total_time = self._trace.total_time
        self.comm_hashmap = [ {} for i in range(self._trace.tasks) ]
        self.mpi_init_hashmap = [ {} for i in range(self._trace.tasks) ]
        self.mpi_fini_hashmap = [ {} for i in range(self._trace.tasks) ]
        self.callstack_pool = [ {} for i in range(self._trace.tasks) ]
        self.mpi_opened = [ False for i in range(self._trace.tasks) ]
        self.burst_last = [ None for i in range(self._trace.tasks) ]
        self.callstack_last = [ None for i in range(self._trace.tasks) ]
        self.loop_stack = [ [] for i in range(self._trace.tasks) ]
        self.mpi_acumm_cycles = [ {} for i in range(self._trace.tasks) ]
    def get_ntasks(self):
        return self._trace.get_ntasks()
    def get_taskids(self):
        return self._trace.get_taskids()
    def parse(self):
        self._trace.parse(
                comms_callback=self.__comms_handler,
                event_callback=self.__event_handler)
        # Reduce merged info
        for rank in range(self._trace.get_ntasks()):
            for cs in self.callstack_pool[rank].values():
                cs.calc_reduce_info()
        return self.callstack_pool[:self._trace.get_ntasks()]

    def __comms_handler(self, rec):
        if rec.logical_send in self.mpi_init_hashmap[rec.task_send_id-1]:
            cs = self.mpi_init_hashmap[rec.task_send_id-1][rec.logical_send]
            cs.add_mpi_msg_size(rec.size)
            cs.set_partner(rec.task_recv_id-1)
            del self.mpi_init_hashmap[rec.task_send_id-1][rec.logical_send]
            rec.send_merged = True
        else:
            self.comm_hashmap[rec.task_send_id-1].update({rec.logical_send:rec})

        if rec.logical_recv in self.mpi_fini_hashmap[rec.task_recv_id-1]:
            cs = self.mpi_fini_hashmap[rec.task_recv_id-1][rec.logical_recv]
            cs.add_mpi_msg_size(rec.size)
            cs.set_partner(rec.task_send_id-1)
            del self.mpi_fini_hashmap[rec.task_recv_id-1][rec.logical_recv]
            rec.recv_merged = True
        else:
            self.comm_hashmap[rec.task_recv_id-1].update({rec.logical_recv:rec})
    def __event_handler(self, rec):
        if len(rec.events["MPI"]) > 0:
            self.__mpi_handler(rec)
        if len(rec.events["HWC"]) > 0:
            self.__hwc_handler(rec)
        if len(rec.events["GLOP"]) > 0:
            self.__glop_handler(rec)
        if len(rec.events["LOOP"]) > 0:
            self.__loops_handler(rec)

    def __loops_handler(self, rec):
        for loop in rec.events["LOOP"]:
            if loop.loopid == "0":
                self.loop_stack[rec.task_id-1].pop()
            else:
                self.loop_stack[rec.task_id-1].append(loop.loopid)
    def __glop_handler(self, rec):
        assert self.mpi_opened[rec.task_id-1]
        assert self.callstack_last[rec.task_id-1][-1].mpi_call_coll
        self.callstack_last[rec.task_id-1].metrics[rec.task_id-1]\
                .update({x.type:x.value for x in rec.events["GLOP"]})
    def __hwc_handler(self, rec):
        hwc_record = list(filter(lambda x: x.type_name == "PAPI_TOT_CYC",
                rec.events["HWC"]))
        if len(hwc_record) > 0:
            assert len(hwc_record) == 1
            hwc_record = hwc_record[0]
            for signature in self.mpi_acumm_cycles[rec.task_id-1].keys():
                self.mpi_acumm_cycles[rec.task_id-1][signature] += hwc_record.value

        if self.mpi_opened[rec.task_id-1]: # MPI call HWC
            self.callstack_last[rec.task_id-1].metrics[rec.task_id-1]\
                    .update({x.type:x.value for x in rec.events["HWC"]})
        else : # Burst HWC
            self.burst_last[rec.task_id-1] = rec
    def __mpi_handler(self, rec):
        assert len(rec.events["MPI"]) == 1
        if rec.events["MPI"][0].value == "0":
            assert self.mpi_opened[rec.task_id-1]
            cs = self.callstack_last[rec.task_id-1]
            cs.metrics[rec.task_id-1]["mpi_duration"] = rec.time - cs.instants[0]
            # On-line merge. It is better in terms of memory usage because 
            # we are compressing information from very beginning
            if not cs.get_signature() in self.callstack_pool[rec.task_id-1]:
                self.callstack_pool[rec.task_id-1].update({cs.get_signature():cs})
            else:
                self.callstack_pool[rec.task_id-1][cs.get_signature()].merge(cs)
                cs = self.callstack_pool[rec.task_id-1][cs.get_signature()]
                # Update self.mpi_init_hashmap with merged callstack
                if cs.instants[-1] in self.mpi_init_hashmap[rec.task_id-1]:
                    self.mpi_init_hashmap[rec.task_id-1][cs.instants[-1]] = cs

            # Recv communication
            if rec.time in self.comm_hashmap[rec.task_id-1]:
                comm = self.comm_hashmap[rec.task_id-1][rec.time]
                cs.set_partner(comm.task_send_id-1)
                cs.add_mpi_msg_size(comm.size)
                if self.comm_hashmap[rec.task_id-1][rec.time].send_merged:
                    del self.comm_hashmap[rec.task_id-1][rec.time]
            else:
                self.mpi_fini_hashmap[rec.task_id-1].update({rec.time: cs})

            self.mpi_acumm_cycles[rec.task_id-1][cs.get_signature()] = 0
            self.mpi_opened[rec.task_id-1] = False
            self.callstack_last[rec.task_id-1] = None
            self.burst_last[rec.task_id-1] = None
        else:
            assert not self.mpi_opened[rec.task_id-1]
            calls = zip(rec.events["LINE"], rec.events["CALL"])
            calls = map(lambda x: (x[0].line,x[1].call_name
                ,x[0].file,None), calls)
            calls = list(calls); calls.reverse()
            mainindex = 0
            for i,c in enumerate(calls):
                if c[1] == "main" or c[1] == "MAIN__":
                    mainindex = i
                                                                                  
            calls = calls[mainindex:]
            calls.append((0,rec.events["MPI"][0].call_name,"libmpi", None))
                                                                                  
            calls = map(lambda x: call(x[0],x[1],x[2],x[3]), calls)
            cs = callstack(rec.task_id-1, rec.time, list(calls))
            if cs.get_signature() in self.mpi_acumm_cycles[rec.task_id-1]:
                cs.iteration_cycles.append(
                        self.mpi_acumm_cycles[rec.task_id-1][cs.get_signature()])
            else:
                self.mpi_acumm_cycles[rec.task_id-1].update({cs.get_signature():0})
                                                                                  
            cs.burst_metrics[rec.task_id-1].update({x.type:x.value 
                for x in self.burst_last[rec.task_id-1].events["HWC"]})
            cs.burst_metrics[rec.task_id-1]["burst_duration"] = \
                rec.time - self.burst_last[rec.task_id-1].time
                                                                                  
            # Send communication
            if rec.time in self.comm_hashmap[rec.task_id-1]:
                comm = self.comm_hashmap[rec.task_id-1][rec.time]
                cs.set_partner(comm.task_recv_id-1)
                cs.add_mpi_msg_size(comm.size)
                if self.comm_hashmap[rec.task_id-1][rec.time].recv_merged:
                    del self.comm_hashmap[rec.task_id-1][rec.time]
            else:
                self.mpi_init_hashmap[rec.task_id-1].update({rec.time: cs})
                                                                                  
            # Loopid information
            cs.loop_info = copy.copy(self.loop_stack[rec.task_id-1])
                                                                                  
            self.callstack_last[rec.task_id-1] = cs
            self.mpi_opened[rec.task_id-1] = True

