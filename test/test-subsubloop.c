#include <stdio.h>
#include <mpi.h>
#include <unistd.h>

#define BUFFER_SIZE 1000

int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);

    int myrank;
    int nranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    char buffer[BUFFER_SIZE];

    for (int i=0; i < 10; ++i)
    {
        MPI_Comm_size(MPI_COMM_WORLD, &nranks);
        for (int j=0; j < 10; ++j)
        {
            MPI_Comm_size(MPI_COMM_WORLD, &nranks);
            int k=0;
            while (k <10)
            {
                MPI_Bcast((void *)buffer, BUFFER_SIZE, MPI_CHAR, 0, MPI_COMM_WORLD);
                MPI_Bcast((void *)buffer, BUFFER_SIZE/2, MPI_CHAR, 0, MPI_COMM_WORLD);
                MPI_Bcast((void *)buffer, BUFFER_SIZE/4, MPI_CHAR, 0, MPI_COMM_WORLD);
                k++;
            }
        }
    }


    MPI_Finalize();
}

