#include <stdio.h>
#include <mpi.h>

void flevel1();
void flevel2();
void flevel3();
void CommSend(int myrank);
void CommRecv(int myrank);


void CommSend(int myrank)
{
    int mydest = myrank + 1;
    int buf = 100;
    MPI_Status st;

    for (int i=0; i<10; i++)
    {
    MPI_Send(&buf, 1, MPI_INT, mydest, 1, MPI_COMM_WORLD);
    MPI_Recv(&buf, 1, MPI_INT, mydest, 1, MPI_COMM_WORLD, &st);
    }
}

void CommRecv(int myrank)
{
    int mysource = myrank - 1;
    int buf = 100;
    MPI_Status st;

    for (int i=0; i<10; i++)
    {
    MPI_Recv(&buf, 1, MPI_INT, mysource, 1, MPI_COMM_WORLD, &st);
    MPI_Send(&buf, 1, MPI_INT, mysource, 1, MPI_COMM_WORLD);
    }
}

void flevel1()
{
    flevel2();
}

void flevel2()
{
    flevel3();
}

void flevel3()
{
    int myrank;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);

    if (myrank%2 == 0)
        CommSend(myrank);
    else
        CommRecv(myrank);
}

int main(int argc, char *argv[])
{
    int myrank, nranks;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    for (int i=0; i<10; ++i)
        flevel1();

    return 0;
}
