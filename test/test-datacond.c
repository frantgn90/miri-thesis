#include <stdio.h>
#include <mpi.h>

#define TAG 1

void CommSend(int myrank, int size);
void CommRecv(int myrank, int size);


void CommSend(int myrank, int size)
{
    int mydest = (myrank + 1) % size;
    int buf = 100;
    MPI_Status st;

    MPI_Send(&buf, 1, MPI_INT, mydest, 1, MPI_COMM_WORLD);
    MPI_Recv(&buf, 1, MPI_INT, mydest, 1, MPI_COMM_WORLD, &st);
}

void CommRecv(int myrank, int size)
{
    int mysource = ((myrank - 1) + size) % size;
    int buf = 100;
    MPI_Status st;

    MPI_Recv(&buf, 1, MPI_INT, mysource, 1, MPI_COMM_WORLD, &st);
    MPI_Send(&buf, 1, MPI_INT, mysource, 1, MPI_COMM_WORLD);
}

int main(int argc, char *argv[])
{
    int myrank, size;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    MPI_Request req;
    MPI_Status st;

    int buf;
    int mysource = ((myrank - 1) + size) % size;
    int mydest = (myrank + 1) % size;

    int mpi_comm = 0;
    for (int i=1; i<=600; ++i)
    {
        if (mpi_comm == 2)
            MPI_Wait(&req, &st);
        else if (mpi_comm == 1)
            MPI_Send(&buf, 1, MPI_INT, mydest, TAG, MPI_COMM_WORLD);
        else
            MPI_Irecv(&buf, 1, MPI_INT, mysource, TAG, MPI_COMM_WORLD, &req);

        mpi_comm = (mpi_comm+1)%3;
    }

    MPI_Finalize();
}
