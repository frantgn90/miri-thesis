#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from loop import loop
from callstack import callstack
from utilities import pretty_print

class edge(object):
    def __init__(self, node_from, node_to):
        self.node_from = node_from
        self.node_to = node_to
        self.ranks = []
        self.times = 0

    def __str__(self):
        return "*{3}* [{0} -> {1}] ({2})"\
                .format(self.node_from.call, self.node_to.call, 
                        list(set(self.ranks)), self.times)


class node(object):
    def __init__(self, call):
        self.call = call
        self.edge_in = []
        self.edge_out = []

#    def connect_in(self, other):
#        for edges_in in self.edge_in:
#            if edges_in.node_from.call == other.call:
#                edges_in.ranks.append(other.call.rank)
#                return False
#
#        my_in = edge(other, self)
#        self.edge_in.append(my_in)
#        other.edge_out.append(my_in)
#        return True

    def connect_out(self, other, rank, increment):
        for edges_out in self.edge_out:
            if edges_out.node_to.call == other.call:
                if isinstance(rank, list):
                    edges_out.ranks.extend(rank)
                else:
                    edges_out.ranks.append(rank)
                edges_out.times += increment
                return False

        my_out = edge(self, other)
        if isinstance(rank, list):
            my_out.ranks.extend(rank)
        else:
            my_out.ranks.append(rank)
        my_out.times += increment
        self.edge_out.append(my_out)
        other.edge_in.append(my_out)
        return True

    def is_head(self):
        return len(self.edge_in) == 0

    def is_tail(self):
        return len(self.edge_out) == 0

    def in_ranks(self):
        res = []
        for edge_in in self.edge_in: 
            res.extend(edge_in.ranks)
        return list(set(res))

    def out_ranks(self):
        res = []
        for edge_out in self.edge_out: 
            res.extend(edge_out.ranks)
        return list(set(res))

    def __str__(self):
        val = ""
        val += "Call = {0}\n".format(self.call)
        val += "In = {0}\n".format(len(self.edge_in))
        for edge in self.edge_in:
            val += "   " + str(edge)+"\n"

        val += "Out = {0}\n".format(len(self.edge_out))
        for edge in self.edge_out:
            val += "   " + str(edge)+"\n"

        return pretty_print(val, "Node")


class flowgraph(object):
    def __init__(self, cluster):
        self._init_node = node(None)
        loop_graphs = []
        for loop in cluster.loops:
            loop_graphs.append(self.__generate_graph(loop))

    def __generate_graph(self, loop_obj):
        graph = [self._init_node]
        subloop_graphs = []

        last_callstack = callstack(0,0,[])
        for new_callstack in loop_obj.program_order_callstacks:
            if isinstance(new_callstack, loop):
                subloop = new_callstack
                subloop_graph = self.__generate_graph(subloop)
                subloop_graph[-1].connect_out(subloop_graph[1], 
                        subloop.get_all_ranks(), subloop.iterations)
                subloop_graphs.append(subloop_graph)

                for n in subloop_graph:
                    print(n)

                print(len(subloop_graph))
                exit(0)

            else:
                if last_callstack.same_flow(new_callstack):
                    # Just update edges values
                    #
                    prev_node = self.__search_node_with_call(graph, 
                            new_callstack.calls[0], None)
                    prev_node = prev_node.edge_in[0].node_from
                    for call_obj in new_callstack.calls:
                        assert not new_node == None
                        done = False
                        for edge_obj in prev_node.edge_out:
                            if edge_obj.node_to.call == call_obj:
                                edge_obj.ranks.append(new_callstack.rank)
                                done = True
                                break
                        assert done
                        prev_node = self.__search_node_with_call(graph, call_obj,
                                None)

                else:
                    common_callstack = last_callstack & new_callstack
                    new_uncommon_callstack = new_callstack - common_callstack
                    last_uncommon_callstack = last_callstack - common_callstack

                    if len(last_uncommon_callstack.calls) == 0:
                        prev_node = graph[0]
                    elif len(new_uncommon_callstack.calls) == 0:
                        prev_node = graph[0]
                    else:
                        last_common_func_call = last_callstack\
                                .get_call_of_func(new_callstack[0].call)
                        prev_node = self.__search_node_with_call(graph, 
                                last_common_func_call, new_callstack.rank)
                        
                        if prev_node == None:
                            # The flow has been broken because a conditional jump
                            # with rank id
                            #
                            prev_node = self.__last_node_with_rank(graph, 
                                    new_callstack.rank)
                        assert not prev_node == None

                    for new_call in new_uncommon_callstack.calls:
                        new_node = self.__search_node_with_call(graph, new_call,
                                new_uncommon_callstack.rank)
                        if not new_node:
                            new_node = node(new_call)
                            graph.append(new_node)

                        prev_node.connect_out(new_node, new_callstack.rank, 1)
                        prev_node = new_node

                last_callstack = new_callstack
        return graph

    def __search_node_with_call(self, graph, call, rank):
        # If rank is None it means that dont care about in ranks
        #
        for node_obj in graph:
            if node_obj.call == call:
                if rank in node_obj.in_ranks() or rank == None:
                    return node_obj
        return None
    def __last_node_with_rank(self, graph, rank):
        
        for node_obj in reversed(graph):
            if rank in node_obj.in_ranks() and not node_obj.call.mpi_call:
                return node_obj
        return None

    def __merge_graphs(self, graphs):
        pass

    def show(self):
        pass
