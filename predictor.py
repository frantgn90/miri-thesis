#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>
#
# Distributed under terms of the MIT license.

import sys, json, copy, subprocess

_graph_outfile="/tmp/graph.gv"
_graph_image="./graph.png"
_graph_command=["dot", "-Tpng", _graph_outfile, "-o", _graph_image]
_graph_display=["display",_graph_image]

## structures ##
prob_tree={}
key_directory={}

## graph ##

def generate_graph(graph):
    graph_fd = open(_graph_outfile, "w")
    graph_fd.write("digraph G {\n")
    
    for major, data in graph.iteritems():
        for minor, data_minor in data.iteritems():
            if minor == "instances": continue
            for dest_major, dest_minor in data_minor["to"].iteritems():
                node_name="{0}.{1}".format(major,str(minor))
                node_name_dest="{0}.{1}".format(dest_major,str(dest_minor))
                node_namex="{0}\\n({1})".format(node_name, str(data_minor["times"]))
                node_namex_dest="{0}\\n({1})".format(node_name_dest, str(graph[dest_major][dest_minor]["times"]))

                graph_fd.write("{0} -> {1}\n".format(node_name,node_name_dest))
                graph_fd.write("{0} [label=\"{1}\"]\n".format(node_name,node_namex))
                graph_fd.write("{0} [label=\"{1}\"]\n".format(node_name_dest,node_namex_dest))


 
    graph_fd.write("}\n")
    graph_fd.close()

def show_graph():
    subprocess.call(_graph_command)
    subprocess.call(_graph_display)


## aux ##
_assigned={}
_lastid=0

def generateid(string):

    global _assigned, _lastid
    if not string in _assigned:
        _assigned.update({string: str(_lastid).zfill(5)})
        _lastid += 1

    return _assigned[string]

def calls(window):
    res = []
    for cs in window:
        res.append(cs.calls)
    return res

def majors(window):
    res = []
    for cs in window:
        res.append(cs.major)
    return res

class stack(object):
    def __init__(self, line):
        self.text = line
        line = line.split("#")
        self.time = line[0]
        self.files = line[1]
        self.lines = line[2]
        self.level = line[3]
        self.calls = line[4]
        self.major = generateid(self.calls)
        self.minor = 1

class windowfy(object):
    def __init__(self, filename, wsize):
        self.filename = filename
        self.file = open(filename, "r")
        self.wsize = wsize
        self._window = [] 
        
        '''
        for i in range(0, wsize):
            self._window.append(stack(self.file.readline()[:-1]))
        '''

    def slide(self):
        newline = self.file.readline()
        if newline == "":
            self.file.close()
            return False

        if len(self._window) < self.wsize:
            self._window.append(stack(newline[:-1]))
        else:
            for i in range(1, self.wsize):
                self._window[i-1] = self._window[i]
            self._window[-1] = stack(newline[:-1])
        return True

    def window(self):
        return self._window


def new_id_with_minor(nodeid):
    global key_directory
    if not nodeid in key_directory:
        key_directory.update({nodeid:[nodeid+".0"]})
    else:
        minor = key_directory[nodeid][-1].split(".")[-1]+1
        key_directory[nodeid].append(nodeid+"."+minor)

    return key_directory[nodeid][-1]


def correct_cs(stack, stack_old):
    lstack = stack.split("|")
    lstack_old = stack_old.split("|")

    # When both callstacks are completelly different
    # it means that there is information between them
    # that we do not have.

    # TODO: Let's see which call we can use instead of this
    # for this purpose, we have to know which patterns are 
    # more frequent. The first approach is to see the predecessor
    # and the preceded callstack

    if set(lstack).intersection(lstack_old) == set([]):
        return None
    
    # It is possible that the call level is so deph that
    # in our 5-level callstack there are not the first levels.
    # Therefore, in this cases we have to add them.
    # e.g.
    #				AA | AZ B  E ---+
    #                  +----------+ |
    #				 J    H V  AZ | (B E)
    #                  +----------+
    #				AA | AZ B  E
    #

    done=False
    tmp=[]
    for i in range(len(lstack_old)-1,-1,-1):
        s = lstack_old[i]
        if s == lstack[-1]:
            if len(tmp) > 0:
                tmp.reverse()
                lstack.extend(tmp)
            done=True
            break
        tmp.append(s)


    #assert(done==True)
    if done is None:
        return None
    return "|".join(lstack)


def polish(window, last_cs):
    # TODO: Delete windows that does not apport info
    # and complete those ones that has been truncated
 
    new_window = []

    if last_cs is None:
        last_cs = window[0]

    old_cs = last_cs

    for cs in window:
        new_cs = copy.deepcopy(cs)
        new_cs.calls = correct_cs(cs.calls, old_cs.calls)
        if not new_cs.calls is None:
            old_cs = new_cs
            new_window.append(new_cs)

    #print "old."+str(calls(window))
    #print "new."+str(calls(new_window))
    return new_window

def _update_tree(tree, node, window):
    assert(len(window) > 0)

    leaf = (len(window) == 1)
    root_major = window[0].major

    # NOTE: We are assuming that the step of the sliding window
    # is 1, therefore, all path from the beginning to the leaf
    # has been done before

    if leaf and root_major in node["to"]:
        minor = node["to"][window[0].major]
        tree[root_major][minor]["times"] += 1
        return True
    elif leaf and not root_major in node["to"]:
        new_minor = 1
        if root_major in tree:
            new_minor = tree[root_major]["instances"]+1
            tree[root_major].update({new_minor:{"times":1,"to":{}}})
            tree[root_major]["instances"]=new_minor
        else:
            tree.update({root_major:{new_minor:{"times":1,"to":{}},"instances":1}})

        node["to"].update({root_major:new_minor})
        return True
    elif not leaf:
        if root_major in node["to"]:
            minor = node["to"][root_major]
            return _update_tree(tree, tree[root_major][minor], window[1:])
        else:
            # There is no possible path
            return False

    assert(False)

def update_tree(tree, window):
    # In the root node, we can follow any path
    root_node = tree[window[0].major]
    for minor, data in root_node.iteritems():
        if minor == "instances": continue

        #if window[0].major in data["to"]:
        updated = _update_tree(tree, tree[window[0].major][minor], window[1:])
        if updated: return


def main(argc, argv):
    cstackinfo = argv[1]
    wsize = int(argv[2])
    window4prediction = list(argv[3:])
    wstackinfo = windowfy(cstackinfo, wsize)

    # NOTE: The first window have only one single node 
    wstackinfo.slide()
    node = wstackinfo.window()[0]
    prob_tree.update(
            {
                node.major: {
                    1:{"times": 1, "to":{}},
                    "instances": 1
                }
            })


    # NOTE: We need this last_cs because could be that the 
    # first c.s. of the next window will be truncated.
    # Is expected that this last_cs has a good value for .calls
    last_cs = None

    while wstackinfo.slide():
        window = wstackinfo.window()
        window = polish(window, last_cs)
        last_cs = window[-1]

        update_tree(prob_tree, window)

    print "Graph data done..."
    
    #generate_graph(prob_tree)
    #show_graph()


    print "Performing the prediction..."
    print window4prediction
    #print json.dumps(prob_tree, sort_keys=True,indent=4, separators=(',', ': '))
       
    return 0

if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
