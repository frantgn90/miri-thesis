/*
 * helper-test.c
 * Copyright (C) 2018 Juan Francisco Martínez Vera <juan.martinez[AT]bsc.es>
 *
 * Distributed under terms of the MIT license.
 */

#include <stdio.h>
#include <mpi.h>
#include <helper.h>

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);

    printf("-> %d\n",helper_loopuid_push(100, "a.c"));
    printf("-> %d\n",helper_loopuid_push(120, "a.c"));
    printf("-> %d\n",helper_loopuid_push(130, "a.c"));

    helper_loopuid_extrae_entry();
    MPI_Barrier(MPI_COMM_WORLD);
    helper_loopuid_extrae_exit();

    helper_loopuid_pop();

    helper_loopuid_extrae_entry();
    MPI_Barrier(MPI_COMM_WORLD);
    helper_loopuid_extrae_exit();

    helper_loopuid_pop();

    helper_loopuid_extrae_entry();
    MPI_Barrier(MPI_COMM_WORLD);
    helper_loopuid_extrae_exit();

    helper_loopuid_pop();

    MPI_Finalize();
    return 0;
}
