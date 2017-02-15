#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import os

if "PARAVER_ON" in os.environ:
    _verbose=False
else:
    _verbose=True

CALLSTACK_SIZE=10

_intra_field_separator="|"
_inter_field_separator="#"

### PARAVER ###

CALLER_EVENT_BASE ="3000000"
CALLIN_EVENT_BASE ="3000010"
MPICAL_EVENT_BASE ="7000000"
MPILIN_EVENT_BASE ="8000000"
MPI_EVENT_BASE    ="5000000"
OMPCAL_EVENT_BASE =""
OMPLIN_EVENT_BASE =""

PARAVER_EVENT     ="2"

FUNC_MAP_FILE     ="functions.map"
MPI_LIB_FILE      ="libmpi_injected.c"

_empty_cell=0

#### CLUSTERING ####

_x_axis_label     ="Number of occurrences"
_y_axis_label     ="Mean period bw occurrences"
_z_axis_label     ="delta"

_x_axis           ="times"
_y_axis           ="time_mean"
_z_axis           ="delta"

_eps              =0.05
_min_samples      =1

#### LOOPS ####

PURELOOP          =0
MULTILOOP         =1

#### PSEUDO-CODE ####

FORLOOP           ="for loop 1 to {0}: [{1}]\n"
IF                ="if {0}:\n"
ELSE              ="elif {0}:\n"
TAB               =":  "


### RANDOM ###
RANDOM_SEED=5748473
