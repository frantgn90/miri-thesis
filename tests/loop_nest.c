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
#define SUBITERS 50
#define MASTER 0
#define TAG 1234
#define TOSLEEP 500

void CommSend(int rank, int partner);
void CommRecv(int rank, int partner, int *val);

void CommSend(int rank, int partner)
{
	int dummy;
	MPI_Comm_rank(MPI_COMM_WORLD, &dummy);
	MPI_Send(&rank, 1, MPI_INT, partner, TAG, MPI_COMM_WORLD);
}

void CommRecv(int rank, int partner, int *val)
{
	int dummy;
	MPI_Comm_rank(MPI_COMM_WORLD, &dummy);
	MPI_Recv(val, 1,MPI_INT, partner, TAG, MPI_COMM_WORLD, NULL);
}

void DoWork()
{
	int i, team, rank;
	for(i=0; i<SUBITERS; ++i)
	{
		usleep(TOSLEEP);
		MPI_Comm_size(MPI_COMM_WORLD, &team);
		MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	}
}

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
			CommSend(rank, rank+1);
			DoWork();
			CommRecv(rank, rank+1, &prank);
		}	
		else
		{
			int prank;
			CommRecv(rank, rank-1, &prank);
			//DoWork();
			CommSend(rank, rank-1);
		}

		// Perform some work
		usleep(TOSLEEP);

		MPI_Barrier(MPI_COMM_WORLD);
	}

	MPI_Barrier(MPI_COMM_WORLD);

	if (rank == MASTER)
		printf("End of execution reached.");

	MPI_Finalize();
}




