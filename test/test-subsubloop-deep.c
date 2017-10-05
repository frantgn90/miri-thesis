#include <stdio.h>
#include <mpi.h>
#include <unistd.h>

void do_work(int level)
{
    for (int j=0; j < 5; ++j)
    {
    usleep(100);
    MPI_Barrier(MPI_COMM_WORLD);
    printf("Pair work done\n");
    }
    if (level < 3)
        do_work(level + 1);
}

int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);

    int myrank;
    int nranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    for (int i=0; i < 20; ++i)
    {
        MPI_Comm_size(MPI_COMM_WORLD, &nranks);
        do_work(0);
    }

    MPI_Finalize();
}

