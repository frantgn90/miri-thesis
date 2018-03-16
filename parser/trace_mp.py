#!/usr/bin/env python

import time
import sys
import glob
import re
import os
import logging
import copy
import numpy
import progressbar
import multiprocessing
from multiprocessing import Pipe,Process

TYPE_STATE = "1"
TYPE_EVENT = "2"
TYPE_COMMS = "3"

MAX_BUFFER_CHUNKS=1000

class stack(object):
    def __init__(self):
        self.stack = []
    def push(self, v):
        self.stack.append(v)
    def top(self):
        return self.stack[-1]
    def pop(self):
        return self.stack.pop()

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
        self.task_send_id = int(self.task_id)
        self.thread_send_id = self.thread_id
        self.logical_send = int(self.fields[5])
        self.physical_send = int(self.fields[6])
        
        self.cpu_recv_id = self.fields[7]
        self.ptask_recv_id = self.fields[8]
        self.task_recv_id = int(self.fields[9])
        self.thread_recv_id = self.fields[10]
        self.logical_recv = int(self.fields[11])
        self.physical_recv = int(self.fields[12])

        self.size = int(self.fields[13])
        self.tag = self.fields[14]

        # Auxiliar variables
        self.recv_merged = False
        self.send_merged = False

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
                    "re":re.compile("991000*")},
                "920000": {"name":"NITER", "class":niter_event,
                    "re":re.compile("992000*")}
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
        self.loop_name = self.pcf.translate_event(self.type, self.loopid)
        self.entry = (self.loopid != "0")
        self.exit = (self.loopid == "0")

class iter_event(event):
    def __init__(self, line, pcf):
        super(iter_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.nested_level = int(self.type)-99100000
        self.iterid = self.fields[7]
        self.entry = (self.iterid != "0")
        self.exit = (self.iterid == "0")

class niter_event(event):
    def __init__(self, line, pcf):
        super(niter_event, self).__init__(line, pcf)
        self.type = self.fields[6]
        self.niters = int(self.fields[7])

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
        self.type_name = self.pcf.translate_type(self.type).split(" ")[0]
        self.type_name_short = self.type_name.split(" ")[0]
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
        if event_type in self.pcfinfo:
            if event_value in self.pcfinfo[event_type]["values"]:
                return self.pcfinfo[event_type]["values"][event_value]
        return "{0}_{1}".format(event_type, event_value)

class trace_mp(object):
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

    def parse(self, 
            comms_callback = lambda x: None, 
            event_callback = lambda x: None, 
            state_callback = lambda x: None, 
            nprocesses=1):
        assert nprocesses != 0

        self.__record_comms_callback = comms_callback
        self.__record_event_callback = event_callback
        self.__record_state_callback = state_callback

        if self.splittrace:
            traces = self.prv_files + [self.comm_file]
        else:
            traces = self.prv_files

        nparsers = 4

        # Reading process
        raw_pipes = [ Pipe(False) for x in range(nparsers) ]
        raw_pipes_recv = list(map(lambda x: x[0], raw_pipes))
        raw_pipes_send = list(map(lambda x: x[1], raw_pipes))
        read_process = Process(target=self._read_trace,  
                args=(traces[0], raw_pipes_send))

        # Parsing process
        parsed_pipes = [ Pipe(False)  for x in range(nparsers) ]
        parsed_pipes_recv = list(map(lambda x: x[0], parsed_pipes))
        parsed_pipes_send = list(map(lambda x: x[1], parsed_pipes))

        parse_processes=[]
        for i in range(nparsers):
            parse_processes.append(Process(target=self._parse_records,args=(
                i,raw_pipes_recv[i], parsed_pipes_send[i])))

        read_process.start()
        for pp in parse_processes: pp.start()

        #self._program_callbacks(nparsers, parsed_pipes_recv)

        read_process.join()
        for pp in parse_processes: pp.join()

    def _read_trace(self, tracefile_name, raw_pipes):
        file_size = os.stat(tracefile_name).st_size
        nparsers = len(raw_pipes)
        i_parser = 0
        lines_buffer=[]
        with open(tracefile_name) as tracefile:
            for line in tracefile:
                lines_buffer.append(line[:-1])
                if len(lines_buffer) >= MAX_BUFFER_CHUNKS:
                    print("[READER] Sending {0} lines to {1}"
                            .format(len(lines_buffer),i_parser))
                    raw_pipes[i_parser].send(lines_buffer)
                    lines_buffer=[]
                    i_parser = (i_parser+1)%nparsers
        for pipe in raw_pipes:
            pipe.send(None)

    def _parse_records(self, workerid, raw_pipe, parsed_pipe):
        lines_set = raw_pipe.recv()
        while not lines_set is None:
            print ("[{0}] Parsing on {1} lines".format(workerid, len(lines_set)))
            parsed_set = []
            for line in lines_set:
                rec = record.new(line, self.pcf)
                if not rec is None:
                    parsed_set.append(rec)
            print ("[{0}] Sending {1} records".format(workerid, len(parsed_set)))
            #parsed_pipe.send(parsed_set)
            print ("[{0}] Receiving".format(workerid))
            lines_set = raw_pipe.recv()
        parsed_pipe.send(None)

    def _program_callbacks(self, nparsers, parsed_pipes):
        end_parsers = []
        i = 0
        while len(end_parsers) < nparsers:
            if i in end_parsers: continue
            set_rec = parsed_pipes[i].recv() # How make non-blocking recv??
            if set_rec is None:
                end_parsers.append(i)
            else:
                for rec in set_rec:
                    if rec.type == TYPE_COMMS:
                        self.__record_comms_callback(rec)
                    elif rec.type == TYPE_EVENT:
                        self.__record_event_callback(rec)
                    elif rec.type == TYPE_STATE:
                        self.__record_state_callback(rec)
            if len(end_parsers) == nparsers: break
            i = (i+1)%nparsers

    def _parse_sequential(self, prv_files):
        for tracefile_name in prv_files:
            file_size = os.stat(tracefile_name).st_size
            trace_simple_name = tracefile_name.split("/")[-1]
            bar = progressbar.ProgressBar(max_value=file_size)
            bar_completed=0
            with open(tracefile_name) as tracefile:
                for line in tracefile:
                    rec = record.new(line[:-1], self.pcf)
                    if rec is None: continue
                    
                    if rec.type == TYPE_COMMS:
                        self.__record_comms_callback(rec)
                    elif rec.type == TYPE_EVENT:
                        self.__record_event_callback(rec)
                    elif rec.type == TYPE_STATE:
                        self.__record_state_callback(rec)
                    bar_completed += len(line)
                    bar.update(bar_completed)
        return None

    def get_ntasks(self):
        if self.splittrace:
            if self.tasks != len(self.prv_files):
                logging.warn("Less files than tasks.")
                return len(self.prv_files)
        return self.tasks
    
    def get_taskids(self):
        if self.splittrace:
            return list(map(lambda x: int(x.split(".")[-1]), self.prv_files))
        return list(range(self.tasks))
