#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Algorithm extracted from thesis 'Towards instantaneous performance analysis using 
coarse-grain sampledand instrumented data'. Harald Servat

At Accurate source code attribution (4.5), pag.82
'''

import constants
import sys, logging

from utilities import is_sublist

_cs_per_thread=100

def get_callstack(csfile):
    vs=[]
    count=0
    times=[]
    with open(csfile, "r") as csfiled:
        for line in csfiled:
            time=line.split(_inter_field_separator)[0]
            cs = line[:-1].split(_inter_field_separator)[-1]
            cs = cs.split(_intra_field_separator)
            cs.reverse()
            vs.append(cs)
            times.append(time)

            #count+=1
            #if _cs_per_thread == count: break

    return vs,times

def searchMostFrequentRoutine(vs):
    routines = {}
    index=0
    for stack in vs:
        for rout in stack:
            if rout in routines:
                routines[rout]["cnt"]+=1
            else:
                routines.update({rout:{"cnt":1,"findex":index}})
        index+=1

    max_times=0
    max_rout=None
    max_index=0
    for r,c in routines.items():
        if c["cnt"]>max_times:
            max_times=c["cnt"]
            max_index=c["findex"]
            max_rout=r

    return max_rout,max_index

def selectPivot(vs):
    routines = {}
    index=0
    for i_stack in range(len(vs)):
        stack = vs[i_stack]
        for rout in stack:
            if rout in routines:
                for i_i_contains_call in routines[rout]["i_contains_call"]:
                    repeated = False
                    if rout in vs[i_i_contains_call]:
                        repeated = True
                        break

                if not repeated:
                    routines[rout]["cnt"]+=1
                    routines[rout]["i_contains_call"].append(i_stack)
            else:
                routines.update({
                    rout:
                    {
                        "cnt":1,
                        "findex":index,
                        "i_contains_call":[i_stack]
                    }})
        index+=1

    max_times=0
    max_rout=None
    max_index=0
    for r,c in routines.items():
        if c["cnt"]>max_times:
            max_times=c["cnt"]
            max_index=c["findex"]
            max_rout=r

    return max_rout,max_index


def getCsContains(vs, pivot):
    result=[]

    for stack in vs:
        if pivot in stack:
            result.append(stack)
    return result

def height_call(callstack, call):
    index = callstack.index(call) # This function raise an exception if value does not exists
    return index

def perform_alignement_st1(vs, vl):
    pivot,firstpivot = searchMostFrequentRoutine(vs)
    #pivot, firstpivot = selectPivot(vs)

    logging.debug("Aligning step 1: Pivot={0} findex={1}"\
            .format(pivot, firstpivot))

    ignored_index=[]
    last_cc_index=firstpivot
    for i in range(firstpivot+1,len(vs)):
        if not pivot in vs[i]: 
            ignored_index.append(i)
            continue
        c_c=vs[i]
        c_cl=vl[i]
        p_c=vs[last_cc_index]
        p_cl=vl[last_cc_index]
        h_cc=height_call(c_c, pivot)
        h_pc=height_call(p_c, pivot)
        if h_cc > h_pc: # Gap back-propataion
            for j in range(i-1,-1,-1):
                to_inject=c_c[:(h_cc-h_pc)]
                to_injectl=c_cl[:(h_cc-h_pc)]
                vs[j]=to_inject+vs[j]
                vl[j]=to_injectl+vl[j]
        elif h_pc > h_cc: # Gap forward propagation
            to_inject=p_c[:(h_pc-h_cc)]
            to_injectl=p_cl[:(h_pc-h_cc)]
            vs[i]=to_inject+vs[i]
            vl[i]=to_inject+vl[i]
        last_cc_index=i

    logging.debug("{0}/{1} callstacks aligned"
            .format((len(vs)-len(ignored_index)), len(vs)))
    return ignored_index

def perform_alignement_st2(vs, vl, ignored_indexes):
    cs_discarded=0
    cs_aligned=0

    logging.debug("Aligning step 2: Realigning {0} ignored stacks"\
                .format(len(ignored_indexes)))

    cnt=0
    for i in ignored_indexes:
        success=False
        discarded=0
        logging.debug("Realignement {0}/{1}: Success={2} Discarded={3}"
                .format(cnt, len(ignored_indexes), cs_aligned, cs_discarded))
        cnt+=1
        while not success:
            sublist=vs[i][discarded:]

            #for j in range(i-1,-1,-1):
            for j in list(set(range(len(vs)))-set(ignored_indexes)):
                iindex=is_sublist(sublist, vs[j])
                if iindex!=-1:
                    success=True
                    if iindex==0: # Fit at the bottom of the callstack
                        if discarded == 0:
                            logging.debug("{0} has been discarded"
                                    .format(str(vs[i])))
                            vs[i]=[] 
                            vl[i]=[]
                            cs_discarded+=1
                            success=True
                            break
                        
                        #assert(discarded > 0)
                        cs_aligned+=1
                        to_inject=vs[i][0:discarded]
                        to_injectl=vl[i][0:discarded]

                        #Propagation of the low frames of the ignored callstack
                        #Assuming all callstacks are equals on its low frames
                        for k in list(set(range(len(vs)))-set(ignored_indexes)):
                            vs[k]=to_inject+vs[k]
                            vl[k]=to_injectl+vl[k]
                        success=True
                        break
                    else:
                        if discarded>0:
                            logging.debug("{0} has been discarded"
                                    .format(str(vs[i])))
                            vs[i]=[]
                            vl[i]=[]
                            cs_discarded+=1
                            success=True
                            break

                        cs_aligned+=1
                        to_inject=list(set(vs[j][:iindex])-set(vs[i]))
                        to_injectl=list(set(vl[j][:iindex])-set(vl[i]))
                        vs[i]=to_inject+vs[i]
                        vl[i]=to_injectl+vl[i]
                        success=True
                        break

            discarded+=1

            if discarded==len(vs[i]):
                logging.debug("{0} has been discarded".format(str(vs[i])))
                vs[i]=[] 
                vl[i]=[]
                cs_discarded+=1
                break

    return cs_discarded, cs_aligned
