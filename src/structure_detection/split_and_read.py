#!/usr/bin/env python

import sys,time,os
from multiprocessing import Pool

def get_app_description(header):
    header = header.split(":")[3:]
    apps_description = []

    napps = int(header[1])
    header = ":".join(header[2:])
    ntasks = int(header.split("(")[0])
    apps_description.append([[]]*ntasks)
    header_threads = header.split("(")[1].split(")")[0]
    
    return ntasks

def parse_trace(infile_name):
    nlines = 0
    with open(infile_name) as infile:
        for line in infile:
            nlines += 1

    return nlines

""" Splitting """
"""---------------------------------------"""

start_time = time.time()
infile_name = sys.argv[1]
assert infile_name[-4:] == ".prv"

infile = open(infile_name)
header = infile.readline()
ntasks = get_app_description(header)

outfile_info_name = infile_name.replace("prv","info")
with open(outfile_info_name,"w") as fd:
    fd.write(header)

outfiles_names = ["{0}.{1}".format(infile_name, i) for i in range(ntasks)]
outfile_comms_name = "{0}.comm".format(infile_name)
outfiles=list(map(lambda x: open(x,"w"), outfiles_names))
outfile_comms = open(outfile_comms_name, "w")

for line in infile:
    if line[0] == "c": # communicator
        continue
    line_args = line.split(":")
    record = int(line_args[0])
    task = int(line_args[3])

    if record == 3: # comms
        outfile_comms.write(line)
    else:
        outfiles[task-1].write(line)

infile.close()

for of in outfiles: of.close()

exit(0)

middle_time = time.time()
print("--- Spl: %s seconds ---" % (middle_time - start_time))

""" Parallel read """
"""---------------------------------------"""

pool = Pool()
res_par = sum(pool.map(parse_trace, outfiles_names))

print("--- Par: %s seconds ---" % (time.time() - middle_time))

""" Sequential read """
"""---------------------------------------"""

start_time = time.time()

infile = open(infile_name)
nlines = 0
infile.readline() # header
for line in infile:
    if line[0] != "c":
        nlines += 1

end_time = time.time()
res_seq = nlines
print("--- Seq: %s seconds ---" % (end_time - start_time))
print("")
print("--- Speedup: {0} ---".format((end_time-start_time)/(start_time-middle_time)))
assert res_seq == res_par
