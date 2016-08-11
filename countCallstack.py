#!/usr/bin/env python 

import sys
import json 

GRAPH_DOT_FILE="graph.gv"
CSTACK_COUNT_FILE="cstack.count"

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

    assert(done==True)
    return "|".join(lstack)


f = sys.argv[1]
cstacks = open(f, "r")

CSTACKS_COUNT = {}
last_cstack = None

for line in cstacks:
    cs="".join(line.split("#")[-1])[:-1]

    if not last_cstack is None:
        cs = correct_cs(cs, last_cstack)
        if cs is None: continue

        if not cs in CSTACKS_COUNT[last_cstack]["probs"]:
            CSTACKS_COUNT[last_cstack]["probs"].update({cs:1})
        else:
            CSTACKS_COUNT[last_cstack]["probs"][cs] += 1

    
    if not cs in CSTACKS_COUNT:
        CSTACKS_COUNT.update({cs:{"times": 1, "probs": {}}})
    else:
        CSTACKS_COUNT[cs]["times"] += 1

    last_cstack = cs

# Generating digraph

fgraph = open(GRAPH_DOT_FILE,"w")
fgraph.write("digraph G {\n")

for k,v in CSTACKS_COUNT.iteritems():
    total = v["times"]
			
    if total > 50:
	    for k1,v1 in v["probs"].iteritems():
		    percent = "{:.3f}".format(float(v1)*100/total) 
			fgraph.write("\"" + k + "\" [style=filled];")

			if float(percent) >= 5:
			    fgraph.write("\"" + k + "\" -> \"" + k1 + "\" [label=\"" + percent + "% \\n(" + str(v1) + ")\"];\n")
                fgraph.write("\"" + k + "\" [label=\"" + k + "\\n(" + str(total) + ")\"];\n")
                fgraph.write("\"" + k1 + "\" [label=\"" + k1 + "\\n(" + str(CSTACKS_COUNT[k1]["times"]) + ")\"];\n")


fgraph.write("}\n")
fgraph.close()

# Graph generated

ofile = open(CSTACK_COUNT_FILE, "w")
json.dump(CSTACKS_COUNT, ofile)
ofile.close()


#print json.dumps(CSTACKS_COUNT, sort_keys=True,indent=4, separators=(',', ': '))

