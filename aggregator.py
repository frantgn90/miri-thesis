#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>
#
# Distributed under terms of the MIT license.

import sys

def aggregate(inputfilesd, outfiled):
    lastlines = [None]*len(inputfilesd)

    end = False
    while True:
        for i in range(len(inputfilesd)):
            if lastlines[i]==None:
                lastlines[i]=inputfilesd[i].readline()[:-1] # remove \n

        # NOTE: Remember that readline returns an empty line when
        # achieve the end of the file
        if len("".join(lastlines))==0:
            break

        min_time = float('inf')
        min_line = None
        for i in range(len(lastlines)):
            if lastlines[i]=="": continue

            time=int(lastlines[i].split(" ")[0])
            if time < min_time:
                min_time=time
                min_line=i

        outfiled.write("{0}\n".format(lastlines[min_line]))
        lastlines[min_line]=None

def Usage(name):
    print("Usage(): {0} function.0.parsed[,function.1.parsed,..., function.N.parsed] output-file".format(name))
    print

def main(argc, argv):
    if argc < 2: Usage(argv[1])

    inputfiles=argv[1:-1]
    nfiles=argc-2
    outfile=argv[-1]

    outfiled=open(outfile, "w")
    inputfilesd=[]

    for i in range(nfiles):
        inputfilesd.append(open(inputfiles[i],"r"))

    aggregate(inputfilesd, outfiled)

if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    exit(main(argc, argv))
