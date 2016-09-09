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

'''
Algorithm extracted from thesis
'Towards instantaneous performance analysis using coarse-grain sampled
and instrumented data'. Harald Servat

-> Accurate source code attribution (4.5), pag.82
'''


import sys

_intra_field_separator="|"
_inter_field_separator="#"

_cs_per_thread=100

def get_callstack(csfile):
    vs=[]
    count=0
    with open(csfile, "r") as csfiled:
        for line in csfiled:
            cs = line[:-1].split(_inter_field_separator)[-1]
            cs = cs.split(_intra_field_separator)
            cs.reverse()
            vs.append(cs)

            #count+=1
            #if _cs_per_thread == count: break

    return vs

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

def getCsContains(vs, pivot):
    result=[]

    for stack in vs:
        if pivot in stack:
            result.append(stack)
    return result

def height_call(callstack, call):
    index = callstack.index(call) # This function raise an exception if value does not exists
    return index

def perform_alignement_st1(vs):
    pivot,firstpivot = searchMostFrequentRoutine(vs)
    #vtmps = getCsContains(vs, pivot)

    print("-> Pivot: {0}".format(pivot))
    print("-> Findex: {0}".format(firstpivot))

    ignored_index=[]
    last_cc_index=firstpivot
    for i in range(firstpivot+1,len(vs)):
        if not pivot in vs[i]: 
            ignored_index.append(i)
            continue
        c_c=vs[i]
        p_c=vs[last_cc_index]
        h_cc=height_call(c_c, pivot)
        h_pc=height_call(p_c, pivot)
        if h_cc > h_pc: # Gap back-propataion
            for j in range(i-1,-1,-1):
                to_inject=c_c[:(h_cc-h_pc)]
                vs[j]=to_inject+vs[j]
        elif h_pc > h_cc: # Gap forward propagation
            to_inject=p_c[:(h_pc-h_cc)]
            vs[i]=to_inject+vs[i]
        last_cc_index=i

    return vs,ignored_index

def perform_alignement_st2(vs, ignored_indexes):
    cs_discarded=0
    cs_aligned=0
    for i in ignored_indexes:
        success=False
        discarded=0
        while not success:
            sublist=vs[i][discarded:]

            #for j in range(i-1,-1,-1):
            for j in list(set(range(len(vs)))-set(ignored_indexes)):
                iindex=is_sublist(sublist, vs[j])
                if iindex!=-1:
                    success=True
                    if iindex==0: # Fit at the bottom of the callstack
                        if discarded == 0:
                            #print("{0} has been discarded".format(str(vs[i])))
                            vs[i]=[]; cs_discarded+=1; success=True
                            break
                        
                        #assert(discarded > 0)
                        cs_aligned+=1
                        to_inject=vs[i][0:discarded]

                        #Propagation of the low frames of the ignored callstack
                        #Assuming all callstacks are equals on its low frames
                        for k in list(set(range(len(vs)))-set(ignored_indexes)):
                            vs[k]=to_inject+vs[k]
                        success=True
                        break
                    else:
                        if discarded>0:
                            #print("{0} has been discarded".format(str(vs[i])))
                            vs[i]=[]; cs_discarded+=1; success=True
                            break

                        #assert(discarded==0)

                        cs_aligned+=1
                        to_inject=list(set(vs[j][:iindex])-set(vs[i]))
                        vs[i]=to_inject+vs[i]
                        success=True
                        break

            discarded+=1

            if discarded==len(vs[i]):
                #print("{0} has been discarded".format(str(vs[i])))
                vs[i]=[]; cs_discarded+=1
                break

    return vs, cs_discarded, cs_aligned
                    
def is_sublist(sl, ll):
    findex=0
    eindex=0

    for i in range(len(ll)):
        if ll[i]==sl[eindex]: 
            if eindex==0: findex=i
            eindex+=1
        else: eindex=0

        if eindex==len(sl): return findex

    return -1

def Usage(name):
    print("Usage(): {0} callstacks-file".format(name))

def main(argc, argv):
    if argc < 2:
        Usage(argv[0])
        return 1

    for csfile in argv[1:]:
        print("Parsing {0} ...".format(csfile))

        vs = get_callstack(csfile) # vs: vector samples
        print("Step 1 ...")
        mat,ignored_index = perform_alignement_st1(vs) # mat: matrix (Sampled) alignement
        print("-> {0} callstacks has been aligned".format(len(mat)-len(ignored_index)))
        print("-> {0} callstacks has been ignored".format(len(ignored_index)))
        print("Done!")
        print("Step 2 ...")
        mat2,cs_discarded, cs_aligned = perform_alignement_st2(mat,ignored_index)
        print("-> {0} callstacks has been aligned".format(cs_aligned))
        print("-> {0} callstack has been discarded".format(cs_discarded))
        print("Done")
        

        outfile = "{0}.aligned".format("".join(csfile.split("/")[-1]))
        outfiled=open(outfile,"w")
    
        for cs in mat2:
            if len(cs)>0:
                outfiled.write(_intra_field_separator.join(cs)+"\n")
            #else:
            #    outfiled.write("*\n")
        outfiled.close()


if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
