#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>
#
# Distributed under terms of the MIT license.

import sys, json

def plot_calls(cstack_count):
    # Identify every callstack with an integer id.


def main(argc, argv):
    count_file = argv[1]
    fcount = open(count_file, "r")
    cstack_count = json.load(fcount)

    plot_calls(cstack_count)

if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    return main(argc, argv)
