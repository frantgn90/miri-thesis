#!/usr/bin/env python

import sys
import json

ENTRY_STR =     "> "
EXIT_STR=       "< "
TIME_SEPARATOR= " "

CSTACKS_COUNT = None

class Stack:
				def __init__(self):
								self.items = []

				def isEmpty(self):
								return self.items == []

				def push(self, item):
								self.items.append(item)

				def pop(self):
								return self.items.pop()

				def peek(self):
								return self.items[len(self.items)-1]

				def size(self):
								return len(self.items)

				def turn(self):
								tmp = []
								while not self.isEmpty():
												tmp.append(self.pop())
								self.items = tmp


def clean_list(lista):
				lista[-1]=lista[-1].replace("\n","")
				return lista

def ltostack(lista):
				res = Stack()

				for l in lista:
								res.push(l)
				return res

def get_complete_stack(stack, old_stack):
				
				#print(stack)
				#print(old_stack)
				#print("..")
				max_count = 0
				candidate = None
				
				while candidate is None or old_stack == "":
								for k,v in CSTACKS_COUNT.iteritems():
									if old_stack in k:
										#print v["probs"]
										for k1,v1 in v["probs"].iteritems():
											if stack in k1 and stack != k1:
															if v1 > max_count:
																			max_count = v1
																			candidate = k1
								break
								old_stack = "|".join(old_stack.split("|")[:-1])

				return candidate

def diff_ops(lstack, lstack_old):

				# When both callstacks are completelly different
				# it means that there is information between them
				# that we do not have.

				# TODO: Let's see which call we can use instead of this
				# for this purpose, we have to know which patterns are 
				# more frequent. The first approach is to see the predecessor
				# and the preceded callstack

				if set(lstack).intersection(lstack_old) == set([]):
								tmp_lstack = get_complete_stack("|".join(lstack), "|".join(lstack_old))

								assert(tmp_lstack != None)
								lstack = tmp_lstack.split("|")

								#return ["xxx"]

				# It is possible that the call level is so deph that
				# in our n-level callstack there are not the first levels.
				# Therefore, in this cases we have to add them.
				# e.g.
				#   AA | AZ B  E ---+
				#      +----------+ |
				#	 J    H V  AZ | (B E)
				#      +----------+
				#   AA | AZ B  E
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

				stack = ltostack(lstack)
				old_stack = ltostack(lstack_old)							

				while stack.peek() == old_stack.peek():
								stack.pop()
								old_stack.pop()

								if stack.size() == 0 or old_stack.size() == 0:
												break

				result = []
				
				old_stack.turn()
				while not old_stack.isEmpty():
								result.append(EXIT_STR + old_stack.pop())

				while not stack.isEmpty():
								result.append(ENTRY_STR + stack.pop())

				return result,lstack

def parse(infile, outfile):
    outfile = open(outfile, "w")
    last_time = 0
    with open(infile, "r") as infi:
        last_stack=[]
        first_stack=infi.readline()
        first_stack_time = first_stack.split("#")[0]
        first_stack = first_stack.split("#")[-1]

        for call in clean_list(first_stack.split("|")):
            last_stack.append(call)
        last_stack.reverse()
        for call in last_stack:
            outfile.write(first_stack_time + TIME_SEPARATOR + ENTRY_STR + call + "\n")
        last_stack.reverse()

        stack_line=infi.readline()
        while stack_line != "":
            time = last_time = stack_line.split("#")[0]
            stack_line = stack_line.split("#")[-1]
            stack = clean_list(stack_line.split("|"))
            ops, stack = diff_ops(stack, last_stack)

            for op in ops:
                #outfile.write(op + "\n")
                outfile.write(time+ TIME_SEPARATOR + op + "\n")

            last_stack = stack
            stack_line=infi.readline()

    # Lastly, all the remaining entries must be exited
    # TODO: Revise...
    for call in last_stack:
        outfile.write("{0} {1}{2}\n".format(str(last_time),EXIT_STR,call))
    outfile.close()

def Usage(name):
    print("Usage: {0} function.0.raw[,...,function.N.raw] cstacks-count-file".format(name))

def main(argc, argv):

    if argc < 2:
        Usage(argv[0])

    global CSTACKS_COUNT
    cstackf = open(argv[-1], "r")
    CSTACKS_COUNT = json.load(cstackf)
    cstackf.close()

    for infile in argv[1:-1]:
        outfile = ".".join(infile.split(".")[:-1]) + ".parsed"

        print("Parsing {0} to {1}".format(infile, outfile))
        parse(infile, outfile)			

if __name__ == "__main__":
	main(len(sys.argv), sys.argv)
