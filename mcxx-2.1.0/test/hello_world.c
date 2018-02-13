/*
 * hello_world.c
 * Copyright (C) 2018 Juan Francisco Martínez <juan.martinez[AT]bsc[dot]es>
 *
 * Distributed under terms of the MIT license.
 */

#include <stdio.h>

int main(int argc, char **argv)
{
    for (int i=0; i<2; ++i)
    {
        for (int j=0; j<2; ++j)
            printf("Hola manola!\n");
    }
    
    #pragma extrae loop
    {
    for (int i=0; i<2; ++i)
        printf("Hola manola!\n");
    }

    return 0;
}



