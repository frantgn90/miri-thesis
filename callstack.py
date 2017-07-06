#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import logging
import numpy
import constants
from delta_calculation import get_cost

class call(object):
    def __init__(self, line, call):
        self.call=call
        self.line=int(line)

    def get_signature(self):
        return "{0}{1}".format(
                self.call, 
                str(self.line))

    def __eq__(self, other):
        if other == None:
            return False
        else:
            return self.call==other.call and self.line == other.line

    def __str__(self):
        val = "{0} ({1})".format(self.call, self.line)
        return val

class callstack(object):
    def __init__(self, rank, instant, calls):
        self.rank=rank
        self.repetitions=1
        self.instants=[int(instant)]
        self.instants_distances=[]
        self.instants_distances_mean=None
        self.instants_distances_median=None
        self.delta=None
        self.cluster_id=None

        self.reduced=False
        self.calls=calls

    @classmethod
    def from_trace(cls, rank, instant, lines, calls):
        assert len(lines)==len(calls), "#lines and #calls must be equal."

        calls_obj = []
        for i in range(0, len(lines)):
            calls_obj.append(call(int(lines[i]), calls[i]))

        return cls(rank, instant, calls_obj)


    def get_line_at_level(self, level):
        return self.calls[level].line

    def get_signature(self):
        signature=""
        for call in self.calls:
            signature += call.get_signature()
        return str(self.rank)+"#"+signature

    def merge(self, other):
        assert self.get_signature() == other.get_signature()
        self.repetitions+=1
        self.instants.extend(other.instants)
 
    def calc_reduce_info(self):
        self.reduced=True
        if self.repetitions == 1: return

        self.instants.sort()
        self.instants_distances=self.__get_distances(self.instants)
        self.instants_distances_median=numpy.median(self.instants_distances)
        self.instants_distances_mean=numpy.mean(self.instants_distances)


    def is_above_delta(self, delta, total_time):
        if self.repetitions == 1: return False
        cost=get_cost(self.repetitions, total_time, self.instants_distances_mean, delta)
        return cost > 0

    def get_instants_dist_median(self):
        return numpy.median(self.instants_distances)

    def get_instants_dist_mean(self):
        return numpy.mean(self.instants_distances)
 
    def __get_distances(self, times):
        dist=[]
        for i in range(1,len(times)):
            dist.append(times[i]-times[i-1])
        return dist
       
    def __eq__(self, other):
        return self.get_signature() == other.get_signature()

    def __lt__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if not self.calls[call_i] == other.calls[call_i]:
#                assert self.calls[call_i].call == other.calls[call_i].call,\
#                        "{0} < {1}".format(self, other)
                if not self.calls[call_i].call == other.calls[call_i].call:
                    logging.warn("Same code line jumps to more than one target"\
                            " locations. Assuming arbitrary order.")
                return self.calls[call_i].line < other.calls[call_i].line

    def __gt__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] != other.calls[call_i]:
                assert self.calls[call_i].call == other.calls[call_i].call
                return self.calls[call_i].line > other.calls[call_i].line

    def __le__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] != other.calls[call_i]:
                assert self.calls[call_i].call == other.calls[call_i].call
                return self.calls[call_i].line <= other.calls[call_i].line

    def __ge__(self, other):
        assert self.reduced == True and other.reduced == True
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] != other.calls[call_i]:
                assert self.calls[call_i].call == other.calls[call_i].call
                return self.calls[call_i].line >= other.calls[call_i].line

    def __and__(self, other):
        result = []
        for call_i in range(min(len(self.calls), len(other.calls))):
            if self.calls[call_i] == other.calls[call_i]:
                result.append(self.calls[call_i])

        result = callstack(self.rank, 0, result)
        ## TODO: Copy the original state to the new object
        return result
         
    def __str__(self):
        val = "[{0}][{1}] {2} calls -".format(self.rank, self.repetitions ,len(self.calls))

#        if len(self.calls) > 3:
#            val += "... -"
#            for i in range(-3, 0):
#                val += ">{0}({1})".format(self.calls[i].call, self.calls[i].line)
#        else:
        for call in self.calls:
            val += ">{0}({1})".format(call.call, call.line)
        return val
