#!/usr/bin/env python

import time
import sys
import glob
import re
import os
import logging
from multiprocessing import Pool

from utilities import ProgressBar
from callstack import call, callstack

TYPE_STATE = "1"
TYPE_EVENT = "2"
TYPE_COMMS = "3"

class record(object):
    def __init__(self,line,pcf):
        self.fields = line.split(":")
        self.type = self.fields[0]
        self.cpu_id = self.fields[1]
        self.appl_id = self.fields[2]
        self.task_id = int(self.fields[3]) # Acts as index in some structures
        self.thread_id = self.fields[4]
        self.pcf = pcf

    @classmethod
    def new(cls, line, pcf):
        rec_type = line[0]
        if rec_type == TYPE_STATE:
            return state(line, pcf)
        elif rec_type == TYPE_EVENT:
            return event(line, pcf)
        elif rec_type == TYPE_COMMS:
            return communication(line, pcf)
        return None


class state(record):
    def __init__(self, line, pcf):
        super(state, self).__init__(line, pcf)
        self.begin_time = self.fields[5]
        self.end_time = self.fields[6]
        self.state = self.fields[7]

class communication(record):
    def __init__(self, line, pcf):
        super(communication, self).__init__(line, pcf)
        self.cpu_send_id = self.cpu_id
        self.ptask_send_id = self.appl_id
        self.task_send_id = self.task_id
        self.thread_send_id = self.thread_id
        self.logical_send = self.fields[5]
        self.physical_send = self.fields[6]
        
        self.cpu_recv_id = self.fields[7]
        self.ptask_recv_id = self.fields[8]
        self.task_recv_id = int(self.fields[9])
        self.thread_recv_id = self.fields[10]
        self.logical_recv = self.fields[11]
        self.physical_recv = self.fields[12]

        self.size = self.fields[13]
        self.tag = self.fields[14]

class event(record):
    def __init__(self, line, pcf):
        super(event, self).__init__(line, pcf)
        self.time = int(self.fields[5])

        if type(self) != event: #inheritage
            return

        self.events_supported = {
                "420000": {"name":"HWC", "class":hwc_event, 
                    "re":re.compile("420000*")},
                "500000": {"name":"MPI", "class":mpi_event, 
                    "re":re.compile("500000*")},
                "501000": {"name":"GLOP", "class":glop_event, 
                    "re":re.compile("501000*")},
                "700000": {"name":"CALL", "class":call_event, 
                    "re":re.compile("700000*")},
                "800000": {"name":"LINE", "class":line_event, 
                    "re":re.compile("800000*")},
                "900000": {"name":"LOOP", "class":loop_event,
                    "re":re.compile("990000*")},
                "910000": {"name":"ITER", "class":iter_event,
                    "re":re.compile("991000*")}
        }

        self.events = {x["name"]:[] for x in self.events_supported.values()}

        for i in range(6,len(self.fields),2):
            event_type = self.fields[i]
            event_value = self.fields[i+1]
            self.insert_event(event_type, event_value)
    
    def insert_event(self, event_type, event_value):
        event_line = "{0}:{1}:{2}".format(":".join(self.fields[:6]),
                event_type,event_value)

        self.events.fromkeys({x["name"] for x in self.events_supported.values() })
        for val in self.events_supported.values():
            if val["re"].match(event_type):
                 self.events[val["name"]].append(val["class"](event_line, self.pcf))

class loop_event(event):
    def __init__(self, line, pcf):
        super(loop_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.nested_level = int(self.type)-99000000
        self.loopid = self.fields[7]

class iter_event(event):
    def __init__(self, line, pcf):
        super(iter_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.nested_level = int(self.type)-99100000
        self.iterid = self.fields[7]
        pass

class glop_event(event):
    def __init__(self, line, pcf):
        super(glop_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.type_name = self.pcf.translate_type(self.type)
        self.value = int(self.fields[7])


class hwc_event(event):
    def __init__(self, line, pcf):
        super(hwc_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.type_name = self.pcf.translate_type(self.type)
        self.value = int(self.fields[7])


class call_event(event):
    def __init__(self, line, pcf):
        super(call_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.value = self.fields[7]
        self.callpath_level = int(self.type[:-2])
        self.call_name = self.pcf.translate_event(self.type, self.value)
        if "[" in self.call_name:
            fromc = self.call_name.index("[")+1
            toc = self.call_name.index("]")
            self.call_name = self.call_name[fromc:toc]

class line_event(event):
    def __init__(self, line, pcf):
        super(line_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.value = self.fields[7]

        self.callpath_level = int(self.type[:-2])
        data = self.pcf.translate_event(self.type, self.value)
        data = data.split(" ")
        if len(data) > 1:
            self.line = data[0]
            data = data[1][1:-1].split(", ")
            self.file = data[0]
            if len(data) > 1:
                self.image = data[1]
            else:
                self.image = ""
        else:
            self.line = ""
            self.image = ""
            self.file = ""

class mpi_event(event):
    def __init__(self, line, pcf):
        super(mpi_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.value = self.fields[7]

        self.mpi_type = int(self.type[:-2])
        self.call_name = self.pcf.translate_event(self.type, self.value)

class pcf(object):
    def __init__(self,pcfname):
        eventtype_del = "EVENT_TYPE"
        values_del = "VALUES"
        self.pcfinfo = {}

        in_event_type = False
        in_event_value = False
        active_event_types=[]
        with open(pcfname) as fd:
            for line in fd:
                if line == "\n": continue
                if "GRADIENT_COLOR" in line or "GRADIENT_NAMES" in line:
                    in_event_value=False
                    in_event_type=False
                    active_event_types=[]
                if eventtype_del in line:
                    in_event_value=False
                    in_event_type=True
                    active_event_types=[]
                    continue
                if values_del in line:
                    in_event_type=False
                    in_event_value=True
                    continue
                if in_event_type:
                    pline = " ".join(line.split()).split(" ")
                    event_key = pline[1]
                    active_event_types.append(event_key)
                    event_name = " ".join(pline[2:])
                    self.pcfinfo.update({
                        event_key:{"name":event_name,"values":{}}
                        })
                    continue
                if in_event_value:
                    pline = " ".join(line.split()).split(" ")
                    value = pline[0]
                    tag = " ".join(pline[1:])
                    for event_key in active_event_types:
                        self.pcfinfo[event_key]["values"].update({value:tag})

    def translate_type(self, event_type):
        return self.pcfinfo[event_type]["name"]

    def translate_event(self, event_type, event_value):
        return self.pcfinfo[event_type]["values"][event_value]


class trace(object):
    def __init__(self, basename):
        self.basename = basename
        if ".prv" in basename:
            self.prv_files = [self.basename]
            self.info_file = self.basename
            self.pcf_file = self.basename.replace(".prv",".pcf")
            self.row_file = self.basename.replace(".prv",".row")
            self.splittrace = False
        else:
            self.prv_files = glob.glob(basename+".prv")
            self.comm_file = glob.glob(basename+".prv.comm")[0]
            self.info_file = glob.glob(basename+".info")[0]
            self.pcf_file = glob.glob(basename+".pcf")[0]
            self.row_file = glob.glob(basename+".row")[0]
            self.splittrace = True

            # Improve by regular expression
            if self.comm_file in self.prv_files:
                del self.prv_files[self.prv_files.index(self.comm_file)]

        with open(self.info_file) as fd:
            self.header = fd.readline()

        # Probably better with regex
        header = self.header[9:].split(":")
        self.trace_date = ":".join(header[0:1])
        self.total_time = int(header[2][:-3])
        self.resources = header[3]
        self.napplications = header[4]

        applications_info = ":".join(header[5:])
        self.tasks = int(applications_info.split("(")[0])

        self.pcf = pcf(self.pcf_file)

    def parse(self, nprocesses=1):
        assert nprocesses != 0

        if nprocesses == 1:
            if self.splittrace:
                traces = self.prv_files + [self.comm_file]
            else:
                traces = self.prv_files
            res = self._parse_sequential(traces)
            for rank in range(self.get_ntasks()):
                for cs in res[rank].values():
                    cs.calc_reduce_info()
        else:
            res = self._parse_parallel(nprocesses)
        return res

    def _parse_sequential(self, prv_files):
        comm_hashmap = [{} for i in range(self.tasks)]
        mpi_init_hashmap = [{} for i in range(self.tasks)]
        mpi_fini_hashmap = [{} for i in range(self.tasks)]
        

        callstack_pool = [{} for i in range(self.tasks)]

        for tracefile_name in prv_files:
            mpi_opened = [False for i in range(self.tasks)]
            burst_last = [None for i in range(self.tasks)]
            callstack_last = [None for i in range(self.tasks)]

            file_size = os.stat(tracefile_name).st_size
            trace_simple_name = tracefile_name.split("/")[-1]
            print ("[{0}] Parsing trace {1}".format(os.getpid(), trace_simple_name))
            with open(tracefile_name) as tracefile:
                for line in tracefile:
                    rec = record.new(line[:-1], self.pcf)
                    if rec is None: continue
                    if rec.type == TYPE_COMMS:
                        ssuccess = rsuccess = False
                        if rec.physical_send in mpi_init_hashmap[rec.task_send_id-1]:
                            cs = mpi_init_hashmap[rec.task_send_id-1][rec.phyisical_send]
                            cs.metrics[rec.task_send_id]["mpi_msg_size"] = rec.size
                            cs.partner.append(rec.task_recv_id)
                            ssuccess = True
                        if rec.physical_recv in mpi_fini_hashmap[rec.task_recv_id-1]:
                            cs = mpi_fini_hashmap[rec.task_recv_id-1][rec.phyisical_recv]
                            cs.metrics[rec.task_recv_id]["mpi_msg_size"] = rec.size
                            cs.partner.append(rec.task_send_id)
                            rsuccess = True
                        if not (ssuccess and rsuccess):
                            comm_hashmap[rec.task_send_id-1].update({rec.physical_send:rec})
                            comm_hashmap[rec.task_recv_id-1].update({rec.physical_recv:rec})
                    elif rec.type == TYPE_EVENT:
                        if len(rec.events["MPI"]) > 0:
                            if rec.events["MPI"][0].value == "0":
                                assert mpi_opened[rec.task_id-1]
                                
                                cs = callstack_last[rec.task_id-1]
                                cs.metrics[rec.task_id-1]["mpi_duration"] = rec.time - cs.instants[0]
                                if rec.time in comm_hashmap[rec.task_id-1]:
                                    comm = comm_hashmap[rec.task_id-1][rec.time]
                                    cs.partner.append(comm.task_send_id)
                                    cs.metrics[rec.task_id-1]["mpi_msg_size"] = comm.size
    
                                # Intra-rank merge
                                if not cs.get_signature() in callstack_pool[rec.task_id-1]:
                                    callstack_pool[rec.task_id-1].update(
                                            {cs.get_signature():cs})
                                else:
                                    callstack_pool[rec.task_id-1][cs.get_signature()].merge(cs)

                                mpi_opened[rec.task_id-1] = False
                                callstack_last[rec.task_id-1] = None
                                burst_last[rec.task_id-1] = None
                            else:
                                assert not mpi_opened[rec.task_id-1]
                                calls = zip(rec.events["LINE"], rec.events["CALL"])
                                calls = map(lambda x: (x[0].line,x[1].call_name,x[0].file,None), calls)
                                calls = list(calls); calls.reverse()
                                mainindex = 0
                                for i,c in enumerate(calls):
                                    if c[1] == "main" or c[1] == "MAIN_":
                                        mainindex = i

                                calls = calls[mainindex:]
                                calls.append((0,rec.events["MPI"][0].call_name,"libmpi", None))

                                calls = map(lambda x: call(x[0],x[1],x[2],x[3]), calls)
                                cs = callstack(rec.task_id-1, rec.time, list(calls))

                                cs.burst_metrics[rec.task_id-1].update({x.type:x.value 
                                    for x in burst_last[rec.task_id-1].events["HWC"]})
                                cs.burst_metrics[rec.task_id-1]["burst_duration"] = \
                                    rec.time - burst_last[rec.task_id-1].time

                                # Send communication
                                if rec.time in comm_hashmap[rec.task_id-1]:
                                    comm = comm_hashmap[rec.task_id-1][rec.time]
                                    cs.partner.append(comm.task_recv_id)
                                    cs.metrics[rec.task_id-1]["mpi_msg_size"] = comm.size

                                callstack_last[rec.task_id-1] = cs
                                mpi_opened[rec.task_id-1] = True

                        if len(rec.events["HWC"]) > 0:
                            if mpi_opened[rec.task_id-1]: # MPI call HWC
                                callstack_last[rec.task_id-1].metrics[rec.task_id-1]\
                                        .update({x.type:x.value for x in rec.events["HWC"]})
                            else : # Burst HWC
                                burst_last[rec.task_id-1] = rec

                        if len(rec.events["GLOP"]) > 0:
                            assert mpi_opened[rec.task_id-1]
                            assert callstack_last[rec.task_id-1][-1].mpi_call_coll

                            callstack_last[rec.task_id-1].metrics[rec.task_id-1]\
                                    .update({x.type:x.value for x in rec.events["GLOP"]})
                        #if len(rec.events["LOOP"]) > 0:
                        #    for l in rec.events["LOOP"]:
                        #        print (l.loopid)

        return callstack_pool[:self.get_ntasks()]

    def _parse_parallel(self, nprocesses):
        assert False, "Not available. TODO: comms buffer should lie on shared memory"
        slice_size = int(len(self.prv_files)/nprocesses)

        slices = []
        for i in range(0,len(self.prv_files),slice_size):
            slice = self.prv_files[i:i+slice_size]
            if len(slices) >= nprocesses:
                to_slice = 0
                for prv_file in slice:
                    slices[to_slice].append(prv_file)
                    to_slice = (to_slice+1)%nprocesses
            else:
                slices.append(slice)

        pool = Pool(nprocesses)
        callpath = pool.map(self._parse_sequential, slices)

    def get_ntasks(self):
        if self.splittrace:
            if self.tasks != len(self.prv_files):
                logging.warn("Less files than tasks.")
                return len(self.prv_files)
        return self.tasks
    
    def get_taskids(self):
        if self.splittrace:
            return list(map(lambda x: int(x.split(".")[-1]), self.prv_files))
        return range(self.tasks)
        

 
# Testing
#basename = sys.argv[1]
#tr = trace(basename)
#start_time = time.time()
#tr.parse(1)
#middle_time = time.time()
#tr.parse(4)
#end_time = time.time()
#seq_time = abs(middle_time-start_time)
#print("SEQ={0}".format(seq_time))
#par_time = abs(end_time-middle_time)
#print("PAR={0}".format(par_time))
#print("SEQ/PAR={0}".format(round(seq_time/par_time, 2)))
