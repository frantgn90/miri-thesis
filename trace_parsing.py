#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import sys, json, re, os

import logging
import constants
from callstack_alignement import *
from utilities import ProgressBar

from callstack import callstack

####### GLOBAL

COUNTER_CALLS = None
COUNTER_TYPE_CALLS = None

CALL_NAMES={}
MPI_CALLS={}
THREAD_DEPH={}
IMAGES={}

CALLER_EVENT=""
CALLIN_EVENT=""

CALLER_EVENT=None
CALLIN_EVENT=None
MPICAL_EVENT=None
MPILIN_EVENT=None
MPI_EVENT=None


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


def parse_events(events,image_filter):
    tmp_call_stack= [""]*constants.CALLSTACK_SIZE
    tmp_image_stack=[""]*constants.CALLSTACK_SIZE
    tmp_line_stack= [""]*constants.CALLSTACK_SIZE 
    tmp_file_stack= [""]*constants.CALLSTACK_SIZE

    ncalls_s=0; nimags_s=0; ncalls_m=0; nimags_m=0; last_time = 0

    # When the callstack is get by mean of the interception of
    # an MPI call, then this call is injected to the top of the 
    # callstack
    mpi_call_to_add=None

    for event_i in range(0, len(events), 2):
        event_key = events[event_i]
        event_value = events[event_i+1]
        
        if event_value=="0": 
            continue
        
        '''
        # NOTE: Callstack get by sampling
        if not CALLER_EVENT.match(event_key) is None:
            tmp_call_stack[int(event_key[-1])]=\
                CALL_NAMES[event_value]["letter"]
            ncalls_s+=1
        elif not CALLIN_EVENT.match(event_key) is None:
            tmp_image_stack[int(event_key[-1])]=\
                    IMAGES[event_value]["image"]
            tmp_line_stack[int(event_key[-1])]=event_value
            tmp_file_stack[int(event_key[-1])]=\
                    IMAGES[event_value]["file"]
            nimags_s+=1
        '''

        # Callstack get by MPI interception
        if not MPICAL_EVENT.match(event_key) is None:
            ncalls_m+=1
            tmp_call_stack[int(event_key[-1])-1]=\
                    CALL_NAMES[event_value]["name"] # "letter"
        elif not MPILIN_EVENT.match(event_key) is None:
            nimags_m+=1
            tmp_image_stack[int(event_key[-1])-1]=IMAGES[event_value]["image"]
            #tmp_line_stack[int(event_key[-1])-1]=event_value
            tmp_line_stack[int(event_key[-1])-1]=IMAGES[event_value]["line"]
            tmp_file_stack[int(event_key[-1])-1]=IMAGES[event_value]["file"]
        elif not MPI_EVENT.match(event_key) is None:
            #MPI_CALLS[event_value]
            mpi_call_to_add=CALL_NAMES["mpi_"+event_value]["name"] 

    assert(ncalls_s==nimags_s)   # For sampling
    assert(ncalls_m==nimags_m)   # For MPI
    assert(ncalls_s&ncalls_m==0) # Disallow both at same time (?)

    ncalls=ncalls_s+ncalls_m
    nimags=nimags_s+nimags_m

    if ncalls > 0:
        filtered_calls=[]; filtered_files=[]
        filtered_lines=[]; filtered_levels=[]

        tmp_call_stack=filter(None,tmp_call_stack)
        for i in range(0, ncalls):
            if tmp_image_stack[i] in image_filter or image_filter == ["ALL"]:
                filtered_calls.append(tmp_call_stack[i])
                filtered_files.append(tmp_file_stack[i])
                filtered_lines.append(tmp_line_stack[i])
                filtered_levels.append(str(i))

        if len(filtered_calls) > 0:
            sampled = "S" if ncalls_s > 0 else "M"
            if sampled == "M":
                assert mpi_call_to_add != None, line
                filtered_calls = [mpi_call_to_add] + filtered_calls
                filtered_files = [constants.MPI_LIB_FILE] + filtered_files
                filtered_lines = ["0"] + filtered_lines 
                filtered_levels= ["0"] + map(lambda x: str(int(x)+1),\
                        filtered_levels)
   
            # Needed for alignement
            filtered_calls.reverse()
            filtered_files.reverse()
            filtered_lines.reverse()
            filtered_levels.reverse()

            # Store the values
            return filtered_calls, filtered_lines, filtered_files
            '''   
            callstack_to_write = str(time-last_time) + FIELD_SEPARATOR + \
                sampled + FIELD_SEPARATOR + \
                "|".join(filtered_files) + FIELD_SEPARATOR + \
                "|".join(filtered_lines) + FIELD_SEPARATOR + \
                "|".join(filtered_levels)+ FIELD_SEPARATOR + \
                "|".join(filtered_calls)
            '''

            ''' 
            cstack_register = sampled + "#" + "|".join(filtered_calls)
            if last_callstack[task-1] != cstack_register:
                task_outfiles_d[task-1].write(callstack_to_write+"\n")
                last_callstack[task-1]=cstack_register
                last_time = time
            '''
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

def get_app_time(trace):
    with open(trace) as tr:
        header = tr.readline()
        appd = get_app_description(header)
        app_time = float(header.split(":")[2].split("_")[0])

    return app_time


def get_callstacks(trace, level, image_filter):
    global CALLER_EVENT, CALLIN_EVENT, MPICAL_EVENT, MPILIN_EVENT, MPI_EVENT

    if level == "0":
        CALLER_EVENT=re.compile(constants.CALLER_EVENT_BASE + ".")
        CALLIN_EVENT=re.compile(constants.CALLIN_EVENT_BASE + ".")
        MPICAL_EVENT=re.compile(constants.MPICAL_EVENT_BASE + ".")
        MPILIN_EVENT=re.compile(constants.MPILIN_EVENT_BASE + ".")
        OMPCAL_EVENT=re.compile(constants.OMPCAL_EVENT_BASE + ".")
        OMPLIN_EVENT=re.compile(constants.OMPLIN_EVENT_BASE + ".")
    else:
        CALLER_EVENT=re.compile(constants.CALLER_EVENT_BASE + str(level))
        CALLIN_EVENT=re.compile(constants.CALLIN_EVENT_BASE + str(level))
        MPICAL_EVENT=re.compile(constants.MPICAL_EVENT_BASE + str(level))
        MPILIN_EVENT=re.compile(constants.MPILIN_EVENT_BASE + str(level))
        OMPCAL_EVENT=re.compile(constants.OMPCAL_EVENT_BASE + str(level))
        OMPLIN_EVENT=re.compile(constants.OMPLIN_EVENT_BASE + str(level))

    MPI_EVENT=re.compile(constants.MPI_EVENT_BASE + ".")

    file_size = os.stat(trace).st_size
    pbar = ProgressBar("Parsing trace", file_size)
    
    with open(trace) as tr:
        header = tr.readline()
        appd = get_app_description(header)

        pbar.progress_by(len(header))

        total_threads = 0
        for task in appd:
            for thread in task:
                total_threads += 1

        global SQUARE_HEIGHT, COUNTER_CALLS, COUNTER_TYPE_CALLS

        COUNTER_TYPE_CALLS = [dict() for x in range(total_threads)]
        COUNTER_CALLS = [0]*total_threads

        ########################
        ### Getting pcf info ###
        ########################
        get_call_names(trace)
        get_line_info(trace)
        get_mpi_calls(trace)

        #######################
        ### Printing images ###
        #######################
        imgs=[]; cnt=0
        for k,v in IMAGES.items():
            if v["image"] == "En": continue # avoid End
            if not v["image"] in imgs and v["line"] != "0":
                imgs.append(v["image"])

        logging.info("Images detected during the execution")

        for im in imgs:
            if im in image_filter or image_filter == ["ALL"]: 
                line = "  {0}".format(im)
            else: 
                line = "  {0} (filtered)".format(im)
            logging.info(line)

        
        #####################
        ### Parsing trace ###
        #####################

        callstack_series=[]
        timestamp_series=[]
        lines_series=[]
        files_series=[]

        for i in range(total_threads):
            callstack_series.append(list())
            timestamp_series.append(list())
            lines_series.append(list())
            files_series.append(list())

        events_buffer = {}
        for line in tr:
            pbar.progress_by(len(line))

            line = line[:-1] # Remove the final \n
            line_fields = line.split(":")

            # Only get the events
            if line_fields[0] == constants.PARAVER_EVENT:
                cpu = int(line_fields[1])
                app = int(line_fields[2])
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
                    events_buffer[buffer_key]={"events":events,
                            "last_time":time}
                    continue
                
                fcalls, flines, ffiles = parse_events(events, image_filter)

                if not fcalls is None:
                    callstack_series[task-1].append(fcalls)
                    timestamp_series[task-1].append(time)
                    lines_series[task-1].append(flines)
                    files_series[task-1].append(ffiles)


            pbar.show()


    # TODO: Terminar de vaciar el events_buffer
    for k,v in events_buffer.items():
        fcalls, flines, ffiles = parse_events(v["events"], image_filter)
        if not fcalls is None:
            callstack_series[task-1].append(fcalls)
            timestamp_series[task-1].append(v["time"])
            lines_series[task-1].append(flines)
            files_series[task-1].append(ffiles)

    # If this aplication is using mpl, then consider it as the very
    # low level MPI call.

    for rank_index in range(len(callstack_series)):
        for i_stack in range(len(callstack_series[rank_index])):
            new_stack_call=[]
            new_stack_line=[]
            new_stack_file=[]

            main = False
            for i_call in range(len(callstack_series[rank_index][i_stack])):
                if callstack_series[rank_index][i_stack][i_call] == "main":
                    main = True
                if not main:
                    continue

                new_stack_call.append(callstack_series[rank_index][i_stack][i_call])
                new_stack_line.append(lines_series[rank_index][i_stack][i_call])
                new_stack_file.append(files_series[rank_index][i_stack][i_call])

                #if "mpl_" in callstack_series[rank_index][i_stack][i_call]:
                #    break

            callstack_series[rank_index][i_stack] = new_stack_call
            lines_series[rank_index][i_stack] = new_stack_line
            files_series[rank_index][i_stack] = new_stack_file
 

#    logging.info("Starting alignement of callstacks")
#
#    for rank_index in range(len(callstack_series)):
#        logging.debug("#{0} Aligning step 1".format(rank_index))
#        ignored_index = perform_alignement_st1(
#                        callstack_series[rank_index],
#                        lines_series[rank_index]) 
#
#        logging.debug("#{0} Aligning step 2".format(rank_index))
#        cs_discarded, cs_aligned =perform_alignement_st2(
#                        callstack_series[rank_index],
#                        lines_series[rank_index],
#                        ignored_index)
#
#        logging.debug("#{0} Aligning done: {1} discarded, {2} aligned"\
#                .format(rank_index,cs_discarded, cs_aligned))
#    logging.info("Done")
 
    callstacks_pool=[]
    for rank in range(len(callstack_series)):
        for cs_i in range(len(callstack_series[rank])):
            new_callstack = callstack.from_trace(rank,
                    timestamp_series[rank][cs_i],
                    lines_series[rank][cs_i], 
                    callstack_series[rank][cs_i],
                    files_series[rank][cs_i])

            try:
                repeated_idx = callstacks_pool.index(new_callstack)
                callstacks_pool[repeated_idx].merge(new_callstack)
            except Exception:
                callstacks_pool.append(new_callstack)

    return callstacks_pool, total_threads
