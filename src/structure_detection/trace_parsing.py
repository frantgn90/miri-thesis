#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, json, re, os

from utilities import ProgressBar
from callstack import callstack

import logging
import constants

####### GLOBAL

CALL_NAMES={}
MPI_CALLS={}
IMAGES={}

CALLER_EVENT=re.compile(constants.CALLER_EVENT_BASE + "*")
CALLIN_EVENT=re.compile(constants.CALLIN_EVENT_BASE + "*")
MPICAL_EVENT=re.compile(constants.MPICAL_EVENT_BASE + "*")
MPILIN_EVENT=re.compile(constants.MPILIN_EVENT_BASE + "*")
MPI_EVENT=re.compile(constants.MPI_EVENT_BASE + ".")

in_mpi_comm = []
comm_size_pushed = []
in_mpi_metric_pushed = []

mpi_durations = None
burst_durations = None 
in_mpi_metric_pushed = {}
metrics = {}

comm_sizes_series = None
comm_partner_series = None
buffer_comm = None
timestamp_series = None


def next_letter(letter):
    letter = list(letter)
    if letter[-1] == "z":
        for i in range(len(letter)-2,-1,-1):
            if letter[i] != "z":
                letter[i]=chr(ord(letter[i])+1)
                letter[i+1:len(letter)-1]="a"*(len(letter)-(i+2))
                return "".join(letter)

        return "a"*(len(letter)+1)
    else:
        letter[-1]=chr(ord(letter[-1])+1)
    return "".join(letter)

def get_pcf_info(event_type, trace):
    pcf_file = trace.replace(".prv", ".pcf")
    in_event_types=False
    in_event_values=False
    in_target_events=False

    values=[]
    with open(pcf_file) as pcfile:
        for line in pcfile:
            if line == "\n": continue
            if "EVENT_TYPE" in line:
                in_event_types=True
                in_event_values=False
                in_target_events=False
            elif "VALUES" in line:
                in_event_types=False
                in_event_values=True
            elif in_event_types:
                in_target_events = (event_type in line) or in_target_events
            elif in_event_values and in_target_events:
                values.append(line)
    return values

def get_line_info(trace):
    global IMAGES

    values = get_pcf_info(constants.CALLIN_EVENT_BASE, trace)
    values.extend(get_pcf_info(constants.MPILIN_EVENT_BASE,trace))

    for line in values:
        if "[" in line:
            line = line[0:line.find(" ")]+" "+line[line.find("[")+1:-1]
        info = line.split(" ")
        l = info[1]

        if len(info) < 4:
            file = image = info[2][1:-1]
        else:
            file = info[2]
            image = info[3]

            if len(file) > 0: file = file[1:-1]
            if len(image) > 0: image = image[:-2]

        IMAGES.update({info[0]: {
            "line" : l,
            "file" : file,
            "image": image}})

def get_call_names(trace):
    global CALL_NAMES

    values = get_pcf_info(constants.CALLER_EVENT_BASE, trace)
    values.extend(get_pcf_info(constants.MPICAL_EVENT_BASE,trace))

    letter="a"   
    for line in values:
        info = line.split(" ")
        name=" ".join(info[1:])

        if "[" in name: entireName=name[name.find("[")+1:-2]
        else: entireName=name[:-1]

        entireName="".join(entireName.split("<")[0])

        CALL_NAMES.update({info[0]: {
            "name":entireName,
            "letter":letter}})
        letter = next_letter(letter)

def get_mpi_calls(trace):
    global MPI_CALLS

    values = get_pcf_info(constants.MPI_EVENT_BASE, trace)
    
    letter = "zzzza" # Could be a problem if there is a lot of
                   # functions, and some of them arrive to zzzz

    for line in values:
        line = line[:-1].split("   ")
        code = line[0]
        name = line[1]

        MPI_CALLS.update({code : name})
        CALL_NAMES.update({
            "mpi_"+code: {
            "name":name,
            "letter":letter}})
        letter=next_letter(letter)


def parse_events(task, time, events):
    global mpi_durations, burst_durations, metrics, comm_sizes_series
    global comm_partner_series, buffer_comm,timestamp_series
    global in_mpi_comm, comm_size_pushed, in_mpi_metric_pushed

    tmp_call_stack= [""]*constants.CALLSTACK_SIZE
    tmp_line_stack= [""]*constants.CALLSTACK_SIZE 
    tmp_file_stack= [""]*constants.CALLSTACK_SIZE

    ncalls_m=0; nimags_m=0; last_time = 0
    mpi_call_to_add=None

    for event_i in range(0, len(events), 2):
        event_key = events[event_i]
        event_value = events[event_i+1]
        call_deph = int(event_key[-2:])-1
       
        if not MPICAL_EVENT.match(event_key) is None:
            tmp_call_stack[call_deph]=CALL_NAMES[event_value]["name"]
            ncalls_m+=1
        elif not MPILIN_EVENT.match(event_key) is None:
            tmp_line_stack[call_deph]=IMAGES[event_value]["line"]
            tmp_file_stack[call_deph]=IMAGES[event_value]["file"]
            nimags_m+=1
        elif not MPI_EVENT.match(event_key) is None:
            if event_value == "0":
                assert in_mpi_comm[task-1]

                if comm_size_pushed[task-1] == False:
                    if time in buffer_comm[task-1]:
                        msg_size = buffer_comm[task-1][time][0]
                        msg_partner = buffer_comm[task-1][time][1]

                        comm_sizes_series[task-1].append(msg_size)
                        comm_partner_series[task-1].append(msg_partner)
                        del buffer_comm[task-1][time]
                    else:
                        comm_sizes_series[task-1].append(0)
                        comm_partner_series[task-1].append([-1])

                mpi_durations[task-1][-1] = time-mpi_durations[task-1][-1]
                burst_durations[task-1].append(time)
                comm_size_pushed[task-1] = False
                in_mpi_comm[task-1] = False

                for m in metrics.keys():
                    if in_mpi_metric_pushed[m][task-1] == False:
                        metrics[m][task-1].append(0)
                    in_mpi_metric_pushed[m][task-1] = False
            else:
                mpi_call_to_add=CALL_NAMES["mpi_"+event_value]["name"] 
                mpi_durations[task-1].append(time)
                timestamp_series[task-1].append(time)
                in_mpi_comm[task-1] = True

                if len(burst_durations[task-1]) == 0:
                    burst_durations[task-1].append(time) # First burst
                else:
                    burst_durations[task-1][-1]=time-burst_durations[task-1][-1]

        elif event_key in metrics.keys():
            if event_value == "0":
                pass
            else:
                metrics[event_key][task-1].append(event_value)
                in_mpi_metric_pushed[event_key][task-1] = True

    assert ncalls_m==nimags_m, "{0} == {1}".format(ncalls_m, nimags_m)

    if ncalls_m > 0:
        assert not mpi_call_to_add is None
        tmp_call_stack = [mpi_call_to_add] + tmp_call_stack
        tmp_file_stack = [constants.MPI_LIB_FILE] + tmp_line_stack
        tmp_line_stack = ["0"] + tmp_line_stack

        tmp_call_stack.reverse()
        tmp_line_stack.reverse()
        tmp_file_stack.reverse()

        mains = ["main", "MAIN__"]
        main_index = tmp_call_stack.index(mains[0]) \
                if mains[0] in tmp_call_stack else -1
        if main_index == -1:
            main_index = tmp_call_stack.index(mains[1]) \
                    if mains[1] in tmp_call_stack else -1
        if main_index == -1:
            logging.warn("No main in {0} : {1}", str(time),str(tmp_call_stack))
            exit(0)
            return None, None, None

        return tmp_call_stack[main_index:],\
                tmp_line_stack[main_index:],\
                tmp_file_stack[main_index:]

    else:
        return None, None, None

def get_app_description(header):
    header = header.split(":")[3:]
    apps_description = []

    # TODO: Support for more than one task
    napps = int(header[1])
    header = ":".join(header[2:])
    ntasks = int(header.split("(")[0])
    apps_description.append([[]]*ntasks)
    header_threads = header.split("(")[1].split(")")[0]
    
    t_index = 0
    for t in header_threads.split(","):
        nthreads = t.split(":")[0]
        apps_description[0][t_index].append(nthreads)
        t_index += 1

    return apps_description

def get_total_threads(header):
    appd = get_app_description(header)
    total_threads = 0
    for task in appd:
        for thread in task:
            total_threads += 1

    return total_threads

def get_app_time(trace):
    with open(trace) as tr:
        header = tr.readline()
        app_time = float(header.split(":")[2].split("_")[0])

    return app_time


def get_callstacks(tracename, metric_types, burst_info):
    file_size = os.stat(tracename).st_size
    pbar = ProgressBar("Parsing trace", file_size)

    get_call_names(tracename)
    get_line_info(tracename)
    get_mpi_calls(tracename)

    global in_mpi_comm, comm_size_pushed, in_mpi_metric_pushed
    global mpi_durations, burst_durations, in_mpi_metric_pushed, metrics
    global comm_sizes_series, comm_partner_series, buffer_comm, timestamp_series

    with open(tracename) as tracefile:
        header = tracefile.readline()
        total_threads = get_total_threads(header)
        pbar.progress_by(len(header))

        mpi_durations = [[] for x in range(total_threads)]
        burst_durations = [[] for x in range(total_threads)]

        for mtype in metric_types:
            metrics.update({mtype:
                [[] for x in range(total_threads)]})
            in_mpi_metric_pushed.update({mtype:
                [False for x in range(total_threads)]})

        callstack_series=[list() for i in range(total_threads)]
        timestamp_series=[list() for i in range(total_threads)]
        lines_series=[list() for i in range(total_threads)]
        files_series=[list() for i in range(total_threads)]
        comm_sizes_series=[list() for i in range(total_threads)]
        comm_partner_series=[list() for i in range(total_threads)]
        buffer_comm=[dict() for i in range(total_threads)]
        in_mpi_comm=[False for i in range(total_threads)]
        comm_size_pushed=[False for i in range(total_threads)]

        events_buffer = {}
        for line in tracefile:
            pbar.progress_by(len(line))
            line = line[:-1] # Remove the final \n
            line_fields = line.split(":")

            if line_fields[0] == constants.PARAVER_EVENT:
                task = int(line_fields[3])
                thread = int(line_fields[4])
                time = int(line_fields[5])
                events = line_fields[6:]
                buffer_key="{0}_{1}".format(task, thread)

                if buffer_key in events_buffer:
                    if events_buffer[buffer_key]["last_time"] == time:
                        events_buffer[buffer_key]["events"].extend(events)
                        continue
                    elif events_buffer[buffer_key]["last_time"] < time:
                        tmp_events=events_buffer[buffer_key]["events"]
                        tmp_time=events_buffer[buffer_key]["last_time"]
                        events_buffer[buffer_key]["events"]=events
                        events_buffer[buffer_key]["last_time"]=time
                        events=tmp_events
                        time=tmp_time
                    else:
                        assert False, "This trace is not time sorted"
                else:
                    events_buffer[buffer_key]={"events":events, "last_time":time}
                    continue
                
                fcalls, flines, ffiles = parse_events(task, time, events)

                if not fcalls is None:
                    callstack_series[task-1].append(fcalls)
                    lines_series[task-1].append(flines)
                    files_series[task-1].append(ffiles)

                assert len(timestamp_series[task-1]) == len(mpi_durations[task-1])

            elif line_fields[0] == constants.PARAVER_COMM:
                assert in_mpi_comm[task-1]
                task_send_id = line_fields[3]
                task_recv_id = int(line_fields[9])
                physic_recv_time = int(line_fields[12])

                message_size = int(line_fields[13])
                comm_sizes_series[task-1].append(message_size)
                comm_partner_series[task-1].append([task_recv_id-1])
                comm_size_pushed[task-1] = True

                if physic_recv_time in buffer_comm[task_recv_id-1]:
                    old_mss_sz = buffer_comm[task_recv_id-1][physic_recv_time]
                    new_message_size = (old_mss_sz[0]+message_size, old_mss_sz[1])
                    buffer_comm[task_recv_id-1][physic_recv_time] = new_message_size
                else:
                    buffer_comm[task_recv_id-1].update({physic_recv_time:
                        (message_size, [task-1])})

    for k,v in events_buffer.items():
        fcalls, flines, ffiles = parse_events(task, time, v["events"])

        if not fcalls is None:
            callstack_series[task-1].append(fcalls)
            timestamp_series[task-1].append(v["time"])
            lines_series[task-1].append(flines)
            files_series[task-1].append(ffiles)

    # Remember Paraver uses next Event Value for show HWC.
    mpi_metrics = {}
    burst_metrics = {}
 
    for key, val in metrics.items():
        if not key == "42000050" and not key == "42000059":
            mpi_metrics.update({key:val})
            continue

        mpi_vals = []
        burst_vals = []
        for rank in range(len(val)):
            mpi_vals.append(val[rank][1::2])
            burst_vals.append(val[rank][0::2])
    
        mpi_metrics.update({key:mpi_vals})
        burst_metrics.update({key:burst_vals})

    total_new_cs = sum(list(map(lambda x: len(x), callstack_series)))
    cpbar = ProgressBar("Reducing callstacks", total_new_cs)

    hashmap={} # Empty hash-map

    for rank in range(len(callstack_series)):
        for cs_i in range(len(callstack_series[rank])):
            new_callstack = callstack.from_trace(rank,
                    timestamp_series[rank][cs_i+1],
                    lines_series[rank][cs_i], 
                    callstack_series[rank][cs_i],
                    files_series[rank][cs_i])

            if new_callstack is None:
                logging.warn("Callstack can not be build up")
                print(rank)
                print(timestamp_series[rank][cs_i+1])
                print(lines_series[rank][cs_i])
                print(callstack_series[rank][cs_i])
                print(files_series[rank][cs_i])
                exit(0)
                continue

            new_callstack.metrics[rank]["mpi_duration"]=\
                mpi_durations[rank][cs_i+1]
            new_callstack.burst_metrics[rank]["burst_duration"]=\
                burst_durations[rank][cs_i+1]
            new_callstack.metrics[rank]["mpi_msg_size"]=\
                comm_sizes_series[rank][cs_i+1]
            new_callstack.set_partner(comm_partner_series[rank][cs_i+1])

            for tmetric, values in mpi_metrics.items():
                new_callstack.metrics[rank].update(
                        {tmetric:int(values[rank][cs_i+1])})
            for tmetric, values in burst_metrics.items():
                new_callstack.burst_metrics[rank].update(
                        {tmetric:int(values[rank][cs_i+1])})

            new_cs_hash = hash(new_callstack.get_signature())
            if new_cs_hash in hashmap:
                for cs in hashmap[new_cs_hash]:
                    if cs == new_callstack:
                        cs.merge(new_callstack)
            else:
                hashmap.update({new_cs_hash:[new_callstack]})

            cpbar.progress_by(1)

    callstacks_pool=[]
    for k,v in hashmap.items():
        callstacks_pool.extend(v)

    # Sanity check
    for cs in callstacks_pool:
        if not cs[-1].mpi_call is True:
            print(cs)
            assert False

    return callstacks_pool, total_threads
