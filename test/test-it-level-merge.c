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

void give(int dest)
{
    int buffer;
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

    MPI_Request *requests = malloc(sizeof(MPI_Request)*NCOMMS);

    if (myrank == MASTER)
        printf("=========\nNº its = %d\n=========\n", NITS);

    MPI_Barrier(MPI_COMM_WORLD);
    for (int ii=0; ii < 50; ++ii)
    {
//    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    for (int i=0; i < NITS; ++i)
    {
        int nrequest = i%NCOMMS;

        if (i < NCOMMS)
        {
            printf("Doing MPI_Irecv (%d) from %d (nreq=%d)\n", 
                    myrank, 
                    recv_from,
                    nrequest);
            ready(recv_from, &requests[nrequest]);
        }
        else if(NCOMMS <= i && i < NCOMMS*2)
        {
            printf("Doing MPI_Send (%d) to %d\n", 
                    myrank, 
                    send_to);
            give(send_to);
        }
        else if(NCOMMS*2 <= i < NCOMMS*3)
        {
            printf("Doing MPI_Wait (%d) (nreq=%d)\n", 
                    myrank,
                    nrequest);
            take(&requests[nrequest]);
        }
        else
        {
            assert(0);
        }
                
    }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    if (myrank == MASTER)
        printf("=========\nFin\n=========\n");
    MPI_Finalize();
}

