#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from __future__ import print_function # Needed by the progress bar

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

def merge_arrays(a, b):
    if len(a) != len(b):
        return None
    #assert len(a) == len(b), "Can not merge arrays with different lenght."

    tlen=(len(a)+len(b))
    c=[None]*tlen

    for i in range(0, tlen, 2):
        if i/2 < len(a): c[i]=a[i/2]
        if i/2 < len(b): c[i+1]=b[i/2]

    return c

def pretty_print(pseudocode, trace_name):
    WIDTH=76
    side=(WIDTH-4-len(trace_name))/2
    if len(trace_name)%2 == 0: offs=2
    else: offs=1

    print("+"+"-"*(side-offs) + "[ " + trace_name + " ]" + "-"*(side) + "+")
    print("|"+" "*(WIDTH-2)+"|")
    pseudocode=pseudocode.split("\n")
    for line in pseudocode:
        pline = "|  " + line + " "*(WIDTH-4-len(line))+"|"
        print(pline)

    print("+"+"-"*(WIDTH-2)+"+")

def print_iterations(iterations):
    outtext=""
    for loop in range(len(iterations)):
        outtext+="CLUSTER {0}\n".format(loop)

        for it in iterations[loop]:
            outtext+="> Iteration_1 found @ [{0} ,{1})\n"\
                    .format(it[0], it[1])

    pretty_print(outtext, "Random iterations by cluster")


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

            print("|{0}>{1}| {2}% {3}/{4}".format("="*(pbar_syms), " "*pbar_spac, str(percent), str(self.progression),str(self.total)), end=endc)
            self.count = 0


def print_matrix(matrix, infile):
    if type(matrix)==list:
        mat=matrix
    else:
        mat=matrix.tolist()

    def format_nums(val):
        return str(val).zfill(12)

    if infile:
        filen=int(np.random.rand()*1000)
        filename="matrix_{0}.txt".format(filen)
        print("---> SAVING TO {0}".format(filename))

        ff=open(filename, "w")
        for row in mat:
            ff.write("\t".join(map(format_nums,row)))
            ff.write("\n")
        ff.close()
    else:
        for row in mat:
            print("\t".join(map(format_nums,row)))

