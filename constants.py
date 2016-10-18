#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

'''
Copyright © 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>

*****************************************************************************
*                        ANALYSIS PERFORMANCE TOOLS                         *
*                              [tool name]                                  *
*                         [description of the tool]                         *
*****************************************************************************
*     ___     This library is free software; you can redistribute it and/or *
*    /  __         modify it under the terms of the GNU LGPL as published   *
*   /  /  _____    by the Free Software Foundation; either version 2.1      *
*  /  /  /     \   of the License, or (at your option) any later version.   *
* (  (  ( B S C )                                                           *
*  \  \  \_____/   This library is distributed in hope that it will be      *
*   \  \__         useful but WITHOUT ANY WARRANTY; without even the        *
*    \___          implied warranty of MERCHANTABILITY or FITNESS FOR A     *
*                  PARTICULAR PURPOSE. See the GNU LGPL for more details.   *
*                                                                           *
* You should have received a copy of the GNU Lesser General Public License  *
* along with this library; if not, write to the Free Software Foundation,   *
* Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA          *
* The GNU LEsser General Public License is contained in the file COPYING.   *
*                                 ---------                                 *
*   Barcelona Supercomputing Center - Centro Nacional de Supercomputacion   *
*****************************************************************************
'''

import os

if "PARAVER_ON" in os.environ:
    _verbose=False
else:
    _verbose=True

CALLSTACK_SIZE=10

_intra_field_separator="|"
_inter_field_separator="#"


CALLER_EVENT_BASE ="3000000"
CALLIN_EVENT_BASE ="3000010"
MPICAL_EVENT_BASE ="7000000"
MPILIN_EVENT_BASE ="8000000"
MPI_EVENT_BASE    ="5000000"


FUNC_MAP_FILE="functions.map"
MPI_LIB_FILE="libmpi_injected.c"

_empty_cell=0

#### CLUSTERING ####

_x_axis_label="Number of occurrences"
_y_axis_label="Mean period bw occurrences"

_x_axis="times"
_y_axis="time_mean"
_z_axis="time_std"

_eps=0.2
_min_samples=1

#### LOOPS ####

PURELOOP=0
MULTILOOP=1

#### PSEUDO-CODE ####

FORLOOP="for loop 1 to {0}: [{1}]\n"
INLOOP_STATEMENT="{0}"
