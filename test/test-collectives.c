#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <unistd.h>

void flevel1(int myrank);
void flevel2();
void flevel3();
void CommSend(int myrank);
void CommRecv(int myrank);


int main(int argc, char *argv[])
{
    int myrank, nranks;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    int *buffer1 = malloc(sizeof(int)*1000);
    int *buffer2 = malloc(sizeof(int)*2000);

    int *inbuffer1 = malloc(sizeof(int)*1000);
    int *inbuffer2 = malloc(sizeof(int)*2000*nranks);

    for (int i=0; i<200; ++i)
    {
        MPI_Reduce((void*) buffer1, (void*) inbuffer1,
                1000, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);
        MPI_Alltoall((void *) buffer2, 2000, MPI_INT,
                (void *) inbuffer2, 2000, MPI_INT, MPI_COMM_WORLD);
    }
    
    MPI_Finalize();
    return 0;
}
