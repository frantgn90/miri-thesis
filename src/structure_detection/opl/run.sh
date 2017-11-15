#! /bin/bash

OPL_LIB="/home/jmartinez/Programas/cplex_studio_126/opl/bin/x86-64_linux/"
OPL_PROJECT="/home/jmartinez/BSC/master/master-thesis/git/src/structure_detection/opl/deltas_fitting"

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$OPL_LIB

$OPL_LIB/oplrun -v -p $OPL_PROJECT real_problem
