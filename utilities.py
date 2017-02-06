#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

def pretty_print(pseudocode, trace_name):
    WIDTH=66
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

