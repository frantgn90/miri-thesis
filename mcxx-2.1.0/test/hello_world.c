/*
 * hello_world.c
 * Copyright (C) 2018 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>
 *
 * Distributed under terms of the MIT license.
 */

#include <stdio.h>
#include <mpi.h>

void just_barrier()
{
    MPI_Barrier(MPI_COMM_WORLD);
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    for (int i=0; i<2; ++i)
    {
        for (int j=0; j<2; ++j)
            printf("Hola manola!\n");
    }
    
    for (int i=0; i<2; ++i)
        just_barrier();

    MPI_Finalize();
    return 0;
}



