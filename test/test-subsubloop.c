#include <stdio.h>
#include <mpi.h>
#include <unistd.h>

void do_work_pair()
{
    usleep(100);
    MPI_Barrier(MPI_COMM_WORLD);
    printf("Pair work done\n");
}

void do_work_odd()
{
    usleep(100);
    MPI_Barrier(MPI_COMM_WORLD);
    printf("Odd work done\n");
}


int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);

    int myrank;
    int nranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    for (int i=0; i < 5; ++i)
    {
        MPI_Comm_size(MPI_COMM_WORLD, &nranks);
        for (int j=0; j < 5; ++j)
        {
            MPI_Comm_size(MPI_COMM_WORLD, &nranks);
            for (int k=0; k < 5; ++k)
            {
                if (! (myrank%2))
                    do_work_pair();
                else
                    do_work_odd();

                if (! (myrank%2))
                    do_work_pair();
                else
                    do_work_odd();
            }
        }
    }


    for (int i=0; i < 10; ++i)
    {
        MPI_Comm_size(MPI_COMM_WORLD, &nranks);
        for (int j=0; j < 5; ++j)
        {
            MPI_Comm_size(MPI_COMM_WORLD, &nranks);
            for (int k=0; k < 5; ++k)
            {
                if (! (myrank%2))
                    do_work_pair();
                else
                    do_work_odd();

                if (! (myrank%2))
                    do_work_pair();
                else
                    do_work_odd();
            }
        }
    }

    for (int i=0; i < 10; ++i)
    {
        MPI_Comm_size(MPI_COMM_WORLD, &nranks);
        for (int j=0; j < 5; ++j)
        {
            MPI_Comm_size(MPI_COMM_WORLD, &nranks);
            for (int k=0; k < 5; ++k)
            {
                if (! (myrank%2))
                    do_work_pair();
                else
                    do_work_odd();

                if (! (myrank%2))
                    do_work_pair();
                else
                    do_work_odd();
            }
        }
    }

    MPI_Finalize();
}

