/*
 * loop.c
 * Copyright (C) 2016 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>
 *
 * Distributed under terms of the MIT license.
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "mpi.h"

#define ITERATIONS 20
#define MASTER 0
#define TAG 1234
#define TOSLEEP 500

int main(int argc, char **argv)
{
	int rank, team;

	MPI_Init(&argc, &argv);
	MPI_Comm_size(MPI_COMM_WORLD, &team);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	if (team%2 != 0)
	{
		printf("Team number must be pair.\n");
		MPI_Finalize();
		exit(1);
	}

	if (rank == MASTER)
		printf("Team: %d\n", team);

	int i=0;
	for (i; i<ITERATIONS; ++i)
	{
		if (rank%2==0)
		{
			int prank;
			MPI_Send(&rank, 1, MPI_INT, rank+1, TAG, MPI_COMM_WORLD);
			MPI_Recv(&prank, 1,MPI_INT, rank+1, TAG, MPI_COMM_WORLD, NULL);
		}	
		else
		{
			int prank;
			MPI_Recv(&prank, 1,MPI_INT, rank-1, TAG, MPI_COMM_WORLD, NULL);
			MPI_Send(&rank, 1, MPI_INT, rank-1, TAG, MPI_COMM_WORLD);
		}

		// Perform some work
		usleep(TOSLEEP);
	}

	MPI_Barrier(MPI_COMM_WORLD);

	if (rank == MASTER)
		printf("End of execution reached.");

	MPI_Finalize();
}




