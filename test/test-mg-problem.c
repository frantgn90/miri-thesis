#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <unistd.h>
#include <assert.h>

#define TAG 1111
#define NCOMMS 25
#define NITS (NCOMMS*3)
#define MASTER 0

void ready(int source, MPI_Request* r)
{
    int buffer;
    MPI_Irecv(&buffer, 1, MPI_INT, source, TAG, MPI_COMM_WORLD, r);
}

void give(int dest, int it)
{
    int buffer;
    it = it%2;

    if (it == 0)
        MPI_Send(&buffer, 1, MPI_INT, dest, TAG, MPI_COMM_WORLD);
    else if (it == 1)
        MPI_Send(&buffer, 1, MPI_INT, dest, TAG, MPI_COMM_WORLD);

}

void take(MPI_Request* r)
{
    MPI_Wait(r, MPI_STATUS_IGNORE);
}

int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);

    int myrank;
    int nranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    int send_to = (myrank+1)%nranks;
    int recv_from = ((myrank-1)+nranks)%nranks;

    MPI_Barrier(MPI_COMM_WORLD);
    for (int ii=0; ii < 200; ++ii)
    {
        MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
        for (int jj=0; jj < 10; ++jj)
        {
            MPI_Request request;
            ready(recv_from, &request);
            give(send_to, ii);
            take(&request);
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    MPI_Finalize();
}

