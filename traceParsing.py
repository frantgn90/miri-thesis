#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>

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


from __future__ import print_function
import sys, json, re, os

from callstackAlignement import *
import constants


####### CONSTANTS

COUNTER_CALLS = None
COUNTER_TYPE_CALLS = None

CALL_NAMES={}
MPI_CALLS={}
THREAD_DEPH={}
IMAGES={}

CALLER_EVENT=""
CALLIN_EVENT=""

####### AUX CLASSES

class Printer():
    def __init__(self,data):                     
        sys.stdout.write("\x1b[K"+data.__str__())
        sys.stdout.flush()

class progress_bar(object):
    def __init__(self, total):
        self.total = total
        self.progression = 0
        self.bar_size=20
        self.update_every=2000
        self.count = 0

    def progress_by(self, by):
        self.progression += by

    def show(self):
        self.count += 1
        if self.count >= self.update_every or self.progression == self.total:
            percent = (self.progression*100)/self.total
            pbar_syms = (self.progression*self.bar_size)/self.total
            pbar_spac = self.bar_size-pbar_syms

            if self.progression == self.total:
                endc="\n"
            else:
                endc="\r"

            print("  [{0}>{1}] {2}% {3}/{4}".format("="*(pbar_syms), " "*pbar_spac, str(percent), str(self.progression),str(self.total)), end=endc)
            self.count = 0


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


def get_callstacks(trace, level, image_filter):
    global CALLER_EVENT, CALLIN_EVENT

    if level == "0":
        CALLER_EVENT=re.compile(constants.CALLER_EVENT_BASE + ".")
        CALLIN_EVENT=re.compile(constants.CALLIN_EVENT_BASE + ".")
        MPICAL_EVENT=re.compile(constants.MPICAL_EVENT_BASE + ".")
        MPILIN_EVENT=re.compile(constants.MPILIN_EVENT_BASE + ".")
    else:
        CALLER_EVENT=re.compile(constants.CALLER_EVENT_BASE + str(level))
        CALLIN_EVENT=re.compile(constants.CALLIN_EVENT_BASE + str(level))
        MPICAL_EVENT=re.compile(constants.MPICAL_EVENT_BASE + str(level))
        MPILIN_EVENT=re.compile(constants.MPILIN_EVENT_BASE + str(level))

    MPI_EVENT=re.compile(constants.MPI_EVENT_BASE + ".")

    file_size = os.stat(trace).st_size
    if constants._verbose: pbar = progress_bar(file_size)
    
    app_time=None
    with open(trace) as tr:
        header = tr.readline()
        if constants._verbose: pbar.progress_by(len(header))
        appd = get_app_description(header)
        app_time = float(header.split(":")[2].split("_")[0])

        total_threads = 0
        for task in appd:
            for thread in task:
                total_threads += 1

        global SQUARE_HEIGHT, COUNTER_CALLS, COUNTER_TYPE_CALLS

        COUNTER_TYPE_CALLS = [dict() for x in range(total_threads)]
        COUNTER_CALLS = [0]*total_threads

        get_call_names(trace)
        get_line_info(trace)
        get_mpi_calls(trace)

        imgs=[]
        cnt=0
        for k,v in IMAGES.items():
            if v["image"] == "En": continue # avoid End
            if not v["image"] in imgs and v["line"] != "0":
                imgs.append(v["image"])

        if constants._verbose:
            img_header ="[Images detected during the execution]"
            print(img_header)

            for im in imgs:
                if im in image_filter or image_filter == ["ALL"]: line = "  {0}".format(im)
                else: line = "  {0} (filtered)".format(im)
                print(line)

        task_outfiles_names=[]
        task_outfiles_d=[]
        for i in range(total_threads):
            new_file_name="functions.{0}.raw".format(i)
            task_outfiles_names.append(new_file_name)
            task_outfiles_d.append(open(new_file_name,"w"))

        # NOTE: Assuming one app

        #last_callstack=[""]*total_threads
        
        if constants._verbose:
            print("[Parsing trace...]")

        callstack_series=[]
        timestamp_series=[]
        lines_series=[]

        for i in range(total_threads):
            callstack_series.append(list())
            timestamp_series.append(list())
            lines_series.append(list())

        for line in tr:
            if constants._verbose: pbar.progress_by(len(line))

            line = line[:-1] # Remove the final \n
            line_fields = line.split(":")

            if line_fields[0] == "2":
                cpu = int(line_fields[1])
                app = int(line_fields[2])
                task = int(line_fields[3])
                thread = int(line_fields[4])
                time = int(line_fields[5])
                events = line_fields[6:]

                tmp_call_stack=[""]*constants.CALLSTACK_SIZE; tmp_image_stack=[""]*constants.CALLSTACK_SIZE
                tmp_line_stack=[""]*constants.CALLSTACK_SIZE; tmp_file_stack=[""]*constants.CALLSTACK_SIZE
                ncalls_s=0; nimags_s=0; ncalls_m=0; nimags_m=0; last_time = 0

                # NOTE: When the callstack is gathered by mean of the interception of
                # an MPI call, then this call is injected to the top of the callstack
                mpi_call_to_add=None

                for event_i in range(0, len(events), 2):
                    event_key = events[event_i]
                    event_value = events[event_i+1]
                    
                    '''
                    # NOTE: Callstack get by sampling
                    if not CALLER_EVENT.match(event_key) is None:
                        tmp_call_stack[int(event_key[-1])]=CALL_NAMES[event_value]["letter"]
                        ncalls_s+=1
                    elif not CALLIN_EVENT.match(event_key) is None:
                        tmp_image_stack[int(event_key[-1])]=IMAGES[event_value]["image"]
                        tmp_line_stack[int(event_key[-1])]=event_value
                        tmp_file_stack[int(event_key[-1])]=IMAGES[event_value]["file"]
                        nimags_s+=1
                    '''
                    # NOTE: Callstack get by MPI interception
                    if not MPICAL_EVENT.match(event_key) is None:
                        tmp_call_stack[int(event_key[-1])]=CALL_NAMES[event_value]["letter"]
                        ncalls_m+=1
                    elif not MPILIN_EVENT.match(event_key) is None:
                        tmp_image_stack[int(event_key[-1])]=IMAGES[event_value]["image"]
                        tmp_line_stack[int(event_key[-1])]=event_value
                        tmp_file_stack[int(event_key[-1])]=IMAGES[event_value]["file"]
                        nimags_m+=1
                    elif not MPI_EVENT.match(event_key) is None:
                        mpi_call_to_add=CALL_NAMES["mpi_"+event_value]["letter"] #MPI_CALLS[event_value]

                assert(ncalls_s==nimags_s)
                assert(ncalls_m==nimags_m)
                assert(ncalls_s&ncalls_m==0)

                ncalls=ncalls_s+ncalls_m
                nimags=nimags_s+nimags_m


                if ncalls > 0:
                    filtered_calls=[]; filtered_files=[]; filtered_lines=[]; filtered_levels=[]

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
                            assert(mpi_call_to_add != None)
                            filtered_calls = [mpi_call_to_add] + filtered_calls
                            filtered_files = [constants.MPI_LIB_FILE] + filtered_files
                            filtered_lines = ["0"] + filtered_lines 
                            filtered_levels= ["0"] + map(lambda x: str(int(x)+1), filtered_levels)

                        # Needed for alignement
                        filtered_calls.reverse()
                        callstack_series[task-1].append(filtered_calls)
                        timestamp_series[task-1].append(time)
                        lines_series[task-1].append(filtered_lines)
            
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
                        

            if constants._verbose: pbar.show()

    if constants._verbose: 
        print("[Starting alignement of callstacks]")

    for rank_index in range(len(callstack_series)):
        mat,ignored_index = perform_alignement_st1(callstack_series[rank_index]) 
        callstack_series[rank_index],cs_discarded, cs_aligned = perform_alignement_st2(mat,ignored_index)

    for rank in range(len(callstack_series)):
        for cs_i in range(len(callstack_series[rank])):
            time=timestamp_series[rank][cs_i]          
            cstack=constants._intra_field_separator.join(callstack_series[rank][cs_i])
            lines=constants._intra_field_separator.join(lines_series[rank][cs_i])
            task_outfiles_d[rank].write("{0}{1}{2}{3}{4}{5}{6}\n"
                    .format(rank, constants._inter_field_separator,
                            time, constants._inter_field_separator,
                            lines,constants._inter_field_separator,
                            cstack, constants._inter_field_separator))

    if constants._verbose: print("[Generating function map file]")
    ofile = open(constants.FUNC_MAP_FILE, "w")
    json.dump(CALL_NAMES, ofile)
    ofile.close()

    

    if constants._verbose:
        print("[Generating temporal data]")
    for i in range(0, total_threads):
        task_outfiles_d[i].close()

    return task_outfiles_names, app_time


