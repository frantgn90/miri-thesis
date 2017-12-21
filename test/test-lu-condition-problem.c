#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <unistd.h>
#include <assert.h>

#define TAG 1111
#define NCOMMS 25
#define NITS (NCOMMS*3)
#define MASTER 0

int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);

    int myrank;
    int nranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    assert(nranks==4);

    int buffer;

    for (int ii=0; ii < 1000; ++ii)
    {
        int send_a = -1;
        int send_b = -1;
        int recv_a = -1;
        int recv_b = -1;

        if (myrank == 0)
        {
            send_a = 1;
            send_b = 2;
        }
        else if (myrank == 1)
        {
            recv_a = 0;
            send_a = 3;
        }
        else if (myrank == 2)
        {
            recv_b = 0;
            send_b = 3;
        }
        else if (myrank == 3)
        {
            recv_a = 1;
            recv_b = 2;
        }
        else
            assert(0);

        if (recv_a >= 0)
            MPI_Recv(&buffer, 1, MPI_INT, recv_a, TAG, MPI_COMM_WORLD,MPI_STATUS_IGNORE);

        if (recv_b >= 0)
            MPI_Recv(&buffer, 1, MPI_INT, recv_b, TAG, MPI_COMM_WORLD,MPI_STATUS_IGNORE);

        if (send_b >= 0)
            MPI_Send(&buffer, 1, MPI_INT, send_b, TAG, MPI_COMM_WORLD);

        if (send_a >= 0)
            MPI_Send(&buffer, 1, MPI_INT, send_a, TAG, MPI_COMM_WORLD);
        
        // Little bit of work
        usleep(100);
    }

    MPI_Finalize();
}

