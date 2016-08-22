#!/usr/bin/env python


'''
./callstack_from_trace.py 

This scripts is the responsible to 
'''

import sys
import json,re

CALLSTACK_SIZE=10

FIELD_SEPARATOR="#"

CALLER_EVENT=""
CALLIN_EVENT=""

CALLER_EVENT_BASE ="3000000"
CALLIN_EVENT_BASE ="3000010"

MPICAL_EVENT_BASE ="7000000"
MPILIN_EVENT_BASE ="8000000"

COUNTER_CALLS = None
COUNTER_TYPE_CALLS = None

CALL_NAMES={}
IMAGES={}

THREAD_DEPH={}

FUNC_MAP_FILE="functions.map"

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

    values = get_pcf_info(CALLIN_EVENT_BASE, trace)

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

            if len(file) > 0:
                file = file[1:-1]
            if len(image) > 0:
                image = image[:-2]

        IMAGES.update({
            info[0]: {
                "line" : l,
                "file" : file,
                "image": image
            }})

def get_call_names(trace):
    global CALL_NAMES

    values = get_pcf_info(CALLER_EVENT_BASE, trace)

    letter="a"   
    for line in values:
        info = line.split(" ")
        name=" ".join(info[1:])

        if "[" in name:
            entireName=name[name.find("[")+1:-2]
        else:
            entireName=name[:-1]

        CALL_NAMES.update({
            info[0]: {
                "name":entireName,
                "letter":letter
                }})
        letter = next_letter(letter)

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

def get_deph(callstack):
    deph = 0
    for call in callstack:
        if call != "_start":
            deph+=1
    return deph


def new_call(appid, taskid, threadid, call):
    global COUNTER_CALLS, COUNTER_TYPE_CALLS

    # NOTE: Assuming one thread per task
    COUNTER_CALLS[taskid-1] += 1
    if not call in COUNTER_TYPE_CALLS[taskid-1]:
        COUNTER_TYPE_CALLS[taskid-1].update({call:1})
    else:
        COUNTER_TYPE_CALLS[taskid-1][call] += 1


    # TODO: Generate the graph step by step

def display_caller_structure(trace, level, image_filter):
    global CALLER_EVENT, CALLIN_EVENT

    if level == "0":
        CALLER_EVENT=re.compile(CALLER_EVENT_BASE + ".")
        CALLIN_EVENT=re.compile(CALLIN_EVENT_BASE + ".")
        MPICAL_EVENT=re.compile(MPICAL_EVENT_BASE + ".")
        MPILIN_EVENT=re.compile(MPILIN_EVENT_BASE + ".")
    else:
        CALLER_EVENT=re.compile(CALLER_EVENT_BASE + str(level))
        CALLIN_EVENT=re.compile(CALLIN_EVENT_BASE + str(level))
        MPICAL_EVENT=re.compile(MPICAL_EVENT_BASE + str(level))
        MPILIN_EVENT=re.compile(MPILIN_EVENT_BASE + str(level))

    with open(trace) as tr:
        # read header
            header = tr.readline()
            appd = get_app_description(header)

            total_threads = 0


            for task in appd:
                for thread in task:
                    total_threads += 1

            global SQUARE_HEIGHT, COUNTER_CALLS, COUNTER_TYPE_CALLS

            COUNTER_TYPE_CALLS = [dict() for x in range(total_threads)]
            COUNTER_CALLS = [0]*total_threads

            get_call_names(trace)
            get_line_info(trace)

            #print json.dumps(CALL_NAMES,sort_keys=True,indent=2, separators=(',', ': '))

            imgs=[]
            cnt=0
            for k,v in IMAGES.items():
                if v["image"] == "En": continue # avoid End
                if not v["image"] in imgs and v["line"] != "0":
                    imgs.append(v["image"])
    
            print("Images detected during the execution")
            print("------------------------------------")
            for im in imgs:
                if im in image_filter or image_filter == ["ALL"]: 
                    print("> {0}".format(im))
                else: 
                    print("  {0}".format(im))


            TASK_OUTFILES = [None]*total_threads

            for i in range(0, total_threads):
                TASK_OUTFILES[i] = open("functions." + str(i) + ".raw", "w")

            # NOTE: Assuming one app

            # NOTE: Two consecutive callstacks must not be equal. If it is, it does not
            # apport any information.

            last_callstack=[""]*total_threads

            for line in tr:
                line = line[:-1] # Remove the final \n
                line_fields = line.split(":")

                if line_fields[0] == "2":
                    cpu = int(line_fields[1])
                    app = int(line_fields[2])
                    task = int(line_fields[3])
                    thread = int(line_fields[4])
                    time = int(line_fields[5])
                    events = line_fields[6:]

                    tmp_call_stack=[""]*CALLSTACK_SIZE; tmp_image_stack=[""]*CALLSTACK_SIZE
                    tmp_line_stack=[""]*CALLSTACK_SIZE; tmp_file_stack=[""]*CALLSTACK_SIZE
                    ncalls_s=0; nimags_s=0; ncalls_m=0; nimags_m=0; last_time = 0

                    for event_i in range(0, len(events), 2):
                        event_key = events[event_i]
                        event_value = events[event_i+1]
                        
                        # NOTE: Callstack get by sampling

                        if not CALLER_EVENT.match(event_key) is None:
                            tmp_call_stack[int(event_key[-1])]=CALL_NAMES[event_value]["name"]
                            ncalls_s+=1
                        elif not CALLIN_EVENT.match(event_key) is None:
                            tmp_image_stack[int(event_key[-1])]=IMAGES[event_value]["image"]
                            tmp_line_stack[int(event_key[-1])]=event_value
                            tmp_file_stack[int(event_key[-1])]=IMAGES[event_value]["file"]
                            nimags_s+=1

                        # NOTE: Callstack get by MPI interception

                        elif not MPICAL_EVENT.match(event_key) is None:
                            tmp_call_stack[int(event_key[-1])]=CALL_NAMES[event_value]["name"]
                            ncalls_m+=1
                        elif not MPILIN_EVENT.match(event_key) is None:
                            tmp_image_stack[int(event_key[-1])]=IMAGES[event_value]["image"]
                            tmp_line_stack[int(event_key[-1])]=event_value
                            tmp_file_stack[int(event_key[-1])]=IMAGES[event_value]["file"]
                            nimags_m+=1

                    assert(ncalls_s==nimags_s)
                    assert(ncalls_m==nimags_m)
                    assert(ncalls_s&ncalls_m==0)

                    ncalls=ncalls_s+ncalls_m
                    nimags=nimags_s+nimags_m

                    if ncalls > 0:
                        filtered_calls=[]; filtered_files=[]; filtered_lines=[]; filtered_levels=[]

                        for i in range(0, ncalls):
                            if tmp_image_stack[i] in image_filter or image_filter == ["ALL"]:
                                filtered_calls.append(tmp_call_stack[i])
                                filtered_files.append(tmp_file_stack[i])
                                filtered_lines.append(tmp_line_stack[i])
                                filtered_levels.append(str(i))

                        if len(filtered_calls) > 0:
                            sampled = "S" if ncalls_s > 0 else "M"
                            callstack_to_write = str(time-last_time) + FIELD_SEPARATOR + \
                                                 sampled + FIELD_SEPARATOR + \
                                                 "|".join(filtered_files) + FIELD_SEPARATOR + \
                                                 "|".join(filtered_lines) + FIELD_SEPARATOR + \
                                                 "|".join(filtered_levels)+ FIELD_SEPARATOR + \
                                                 "|".join(filtered_calls)
                            
                            cstack_register = sampled + "#" + "|".join(filtered_calls)
                            if last_callstack[task-1] != cstack_register:
                                TASK_OUTFILES[task-1].write(callstack_to_write+"\n")
                                last_callstack[task-1]=cstack_register
                                last_time = time

    for i in range(0, total_threads):
        TASK_OUTFILES[i].close()


def main(argc, argv):
    if argc < 2:
        print("Usage(): {0} [-l call_level] [-f img1[,img2,...]] <trace>".format(argv[0]))
        print 
        return -1


    trace = argv[-1]
    level=0
    image_filter=None

    for i in range(1, len(argv)-1):
        if argv[i] == "-f":
            image_filter=argv[i+1].split(",")
        elif argv[i] == "-l":
            level=argv[i+1]

    clevels = "All"
    if level != "0":
        clevels=str(level)

    print("{0} : Calls level={1}; Image filter={2}; Trace=[../]{3}\n\n".format(argv[0], clevels, str(image_filter), trace.split("/")[-1]))
    display_caller_structure(trace, level, image_filter)

    print("Generating function to letter mapping file")
    ofile = open(FUNC_MAP_FILE, "w")
    json.dump(CALL_NAMES, ofile)
    ofile.close()

    print("Done")
    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))