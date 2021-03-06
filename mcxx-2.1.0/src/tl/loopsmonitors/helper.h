/*
 * helper.h
 * Copyright (C) 2018 Juan Francisco Martínez Vera <juan.martinez[AT]bsc.es>
 *
 * Distributed under terms of the MIT license.
 */

#ifndef HELPER_H
#define HELPER_H

#ifdef __cplusplus
extern "C"
{
#endif

#define HASHMAP_SIZE 100
#define TRUE 1
#define FALSE 0

#define INTERFACE_ALIASES_F(fname,params,rettype) \
    rettype fname##_ params __attribute__ ((alias (#fname)));

#include <extrae.h>
#include <defines.h>

/* Data structures */


struct loopid_container
{
    unsigned int id;
    unsigned int line;
    char *file_name;
};
typedef struct loopid_container loopid_container;

struct hashmap_entry
{
    loopid_container *info;
    struct hashmap_entry *next;
};
typedef struct hashmap_entry hashmap_entry;

struct hashmap_entry_top
{
    hashmap_entry *first;
    unsigned int size;
};
typedef struct hashmap_entry_top hashmap_entry_top;

struct loopid_item
{
    struct loopid_item *next;
    extrae_value_t val;
};
typedef struct loopid_item loopuid_item;

struct loopuid_stack
{
    loopuid_item *top;
    unsigned int size;
};
typedef struct loopuid_stack loopuid_stack;

//static int last_loop_id = 0;
extern loopuid_stack my_stack;
extern loopuid_stack decission_stack;
extern loopuid_stack itercounter_stack;
extern unsigned int helper_initialized;
extern hashmap_entry_top loopid_hashmap[HASHMAP_SIZE];

/* Functions */

unsigned int
get_loop_hash(
        unsigned int line, 
        char *file_name);

//unsigned int 
//get_loop_uid(
//        unsigned int line, 
//        char *file);

loopuid_stack * 
new_loopuidstack();

unsigned int 
loopuidstack_size(
        loopuid_stack *stack);


void 
loopuidstack_push(
        loopuid_stack *stack, 
        extrae_value_t id);

extrae_value_t 
loopuidstack_pop(
        loopuid_stack *stack);

char * 
loopuidstack_tostr(
        loopuid_stack *stack);

unsigned int
loopuidstack_tov(
        loopuid_stack *stack, 
        extrae_value_t **res);

// This interface is a bit easier to manage
// with Mercurium

void
helper_loopuid_push(
        unsigned int line,
        char *file_name);

void
helper_loopuid_pop();

void 
helper_loopuid_stack_extrae_entry();

void 
helper_loopuid_stack_extrae_exit();

void 
helper_loop_entry(
        unsigned int line, 
        char *file_name);

void 
helper_loop_exit();

void 
helper_loop_iter_entry(
        double chance);

void 
helper_loop_iter_exit();

void
helper_init();

void 
helper_fini();

#ifdef __cplusplus
}
#endif


#endif /* !HELPER_H */
