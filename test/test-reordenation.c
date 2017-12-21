#include <stdio.h>
#include <mpi.h>
#include <unistd.h>

void CommSend(int myrank, int nranks);
void CommRecv(int myrank, int nranks);

void CommSend(int myrank, int nranks)
{
    int mydest = (myrank+1) % nranks;
    int buf = 100;
    MPI_Status st;

    MPI_Send(&buf, 1, MPI_INT, mydest, 1, MPI_COMM_WORLD);
    usleep(100);
    MPI_Recv(&buf, 1, MPI_INT, mydest, 1, MPI_COMM_WORLD, &st);
}

void CommRecv(int myrank, int nranks)
{
    int mysource = (myrank-1+nranks) % nranks;
    int buf = 100;
    MPI_Status st;

    MPI_Recv(&buf, 1, MPI_INT, mysource, 1, MPI_COMM_WORLD, &st);
    MPI_Send(&buf, 1, MPI_INT, mysource, 1, MPI_COMM_WORLD);
}

int main(int argc, char *argv[])
{
    int rank, nranks;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    for (int i=0; i<200; ++i)
    {
        if (rank % 2)
            CommSend(rank,nranks);
        else
            CommRecv(rank,nranks);
        if (rank % 2)
            CommSend(rank,nranks);
        else
            CommRecv(rank,nranks);

        MPI_Barrier(MPI_COMM_WORLD);

        if (rank % 2)
            CommSend(rank,nranks);
        else
            CommRecv(rank,nranks);
        if (rank % 2)
            CommSend(rank,nranks);
        else
            CommRecv(rank,nranks);

    }
    MPI_Finalize();
    return 0;
}
