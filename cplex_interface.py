#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import os
import tempfile

import constants

class CplexInterface(object):
    
    def __init__(self):
        self.outdir = tempfile.mkdtemp(prefix="struct-gen.cplex.")
        self.outfile = "{0}/{1}".format(self.outdir, result.txt)

    def setInput(self, input_file):
        assert os.path.isfile(input_file)

        self.input_file = input_file
        os.symlink(self.input_file, OPL_PROBLEM_INPUT)

