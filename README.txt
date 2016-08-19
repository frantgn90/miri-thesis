README.txt

:Author: Juan Francisco Martínez
:Email: juan.martinez[AT]bsc[dot]es
:Date: 2016-08-18 11:44

> trace2raw.py: Get all the information regarding the callstacks (only from sampling) from the paraver trace and generates
another trace file.

> raw2func.py: Translates the trace file that has been generated with trace2raw.py to a sequence of entries/exits to/from 
the functions. i.e. Instead of having a sequence of callstacks, we have a sequence of entries and exits. There are generated
calculing the differences between the consecutive callstacks,

> countCallstack.py: <DEPRECATED> Performs a counting of how many times a callstack is followed by other one. It has been used because there are
situtations in which ones raw2func can not calculate the differences between to callstacks. Then the most probable callstack will be
injected.

> predictor.py: Generates a probability graph and perform predictions by mean of an input callstack

> timesProfiler.py: Show the mean of duration of every function



