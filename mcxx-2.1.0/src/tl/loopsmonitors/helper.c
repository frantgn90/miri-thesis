/*
 * helper.c
 * Copyright (C) 2018 Juan Francisco Martínez Vera <juan.martinez[AT]bsc.es>
 *
 * Distributed under terms of the MIT license.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <helper.h>
#include <time.h>

loopuid_stack my_stack = { .top = NULL, .size = 0 };
loopuid_stack decission_stack = { .top = NULL, .size = 0 };
loopuid_stack itercounter_stack = { .top = NULL, .size = 0 };
unsigned int rand_init = FALSE;
unsigned int env_chance = FALSE;
double env_chance_value = 0;
hashmap_entry_top loopid_hashmap[HASHMAP_SIZE];

unsigned int
get_loop_hash(unsigned int line, char *file_name)
{
    /* https://stackoverflow.com/questions/7666509/hash-function-for-string */

    unsigned int ndigits = 0;
    unsigned int nchars = strlen(file_name);
    unsigned int ll = line;
    while (ll > 0) 
    {
        ++ndigits;
        ll /= 10;
    }

    char str[nchars+ndigits+2];
    memcpy((void *)&str[0], (void *)file_name, nchars);
    snprintf(&str[nchars], ndigits+2, "_%d", line);

    unsigned int hash = 5381;
    int c, i=0;

    while (c = str[i++])
        hash = ((hash << 5) + hash) + c; /* hash * 33 + c */

    return hash;
}

//unsigned int
//get_loop_hash(unsigned int line, char *file_name)
//{
//    unsigned int hash = 0;
//    for(int i=0; i<strlen(file_name); ++i)
//    {
//        hash ^= file_name[i];
//    }
//    hash ^= line;
//    return hash;
//}

//unsigned int 
//get_loop_uid(unsigned int line, char *file_name)
//{
//    unsigned int hm_key = line % HASHMAP_SIZE;
//    hashmap_entry_top *hm_entry_top = &loopid_hashmap[hm_key];
//
//    hashmap_entry *item = hm_entry_top->first;
//    unsigned int entry_size = hm_entry_top->size;
//
//    for (int i=0; i<entry_size; ++i)
//    {
//        if (item->info->line == line
//                && item->info->file_name == file_name)
//        {
//            return item->info->id;
//        }
//        item = item->next;
//    }
//
//    loopid_container *new_info = (loopid_container *) 
//        malloc(sizeof(loopid_container));
//    new_info->line = line;
//    new_info->file_name = file_name;
//    new_info->id = last_loop_id++;
//
//    hashmap_entry *new_hm_entry = (hashmap_entry *)
//        malloc(sizeof(hashmap_entry));
//    new_hm_entry->info = new_info;
//    new_hm_entry->next = hm_entry_top->first;
//
//    hm_entry_top->first = new_hm_entry;
//    hm_entry_top->size++;
//
//    return new_info->id;
//}

loopuid_stack * 
new_loopuidstack()
{
    loopuid_stack *res = malloc(sizeof(loopuid_stack));
    res->top = NULL;
    res->size = 0;

    return res;
}

void 
loopuidstack_push(loopuid_stack *stack, extrae_value_t id)
{
    loopuid_item *new_item = (loopuid_item *) malloc(sizeof(loopuid_item));
    new_item->val = id;
    new_item->next = stack->top;
    stack->top = new_item;
    stack->size += 1;
}

extrae_value_t 
loopuidstack_pop(loopuid_stack *stack)
{
    if (loopuidstack_size(stack) == 0)
        return 0;

    loopuid_item *top = stack->top;
    stack->top = top->next;
    stack->size -= 1;
    unsigned int res = top->val;
    free(top);

    return res;
}

loopuid_item *
loopuidstack_top(loopuid_stack *stack)
{
    return stack->top;
}

unsigned int 
loopuidstack_size(loopuid_stack *stack)
{
    return stack->size;
}

unsigned int
loopuidstack_tov(loopuid_stack *stack, extrae_value_t **r)
{
    unsigned int size = loopuidstack_size(stack);
    if (size == 0)
    {
        *r = NULL;
        return 0;
    }

    unsigned int res_i = 0;
    extrae_value_t *res = (extrae_value_t *) 
        malloc(sizeof(extrae_value_t)*size);

    loopuid_item *iterator = stack->top;
    while (iterator != NULL)
    {
        res[res_i++] = iterator->val;
        iterator = iterator->next;
    }
    *r = res;
    return size;
}

char * 
loopuidstack_tostr(loopuid_stack *stack)
{
    unsigned int size = loopuidstack_size(stack);
    if (size == 0)
        return "";

    int char_size = 3;
    char separator ='|';
    char *res = (char *) malloc(size*(char_size+1)+1);
    unsigned int res_i = 0;

    loopuid_item *iterator = stack->top;
    while(iterator != NULL)
    {
        snprintf(&res[res_i],char_size+1,"%03d",iterator->val);
        res[res_i+char_size]=separator;
        iterator = iterator->next;
        res_i+=(char_size+1);
    }
    res[res_i-1]='\0';
    return res;
}

INTERFACE_ALIASES_F(helper_loopuid_push,
        (unsigned int line, char * file_name), void)
void helper_loopuid_push(unsigned int line, char *file_name)
{
    unsigned int hash = get_loop_hash(line, file_name);
    loopuidstack_push(&my_stack, (extrae_value_t)hash);
}

INTERFACE_ALIASES_F(helper_loopuid_pop, (), void)
void helper_loopuid_pop()
{
    loopuidstack_pop(&my_stack);
}

INTERFACE_ALIASES_F(helper_loopuid_stack_extrae_entry,(),void)
void helper_loopuid_stack_extrae_entry()
{
    unsigned int size;
    extrae_type_t *types;
    extrae_value_t *values;

    size = loopuidstack_tov(&my_stack, &values);
    types = (unsigned int *) malloc(sizeof(extrae_value_t)*size);
    for (int i=0; i<size; ++i)
    {
        types[i] = EXTRAE_LOOPEVENT+i;
    }

    Extrae_nevent(size, types, values);

    free(types);
    free(values);
}

INTERFACE_ALIASES_F(helper_loopuid_stack_extrae_exit,(),void)
void helper_loopuid_stack_extrae_exit()
{
    unsigned int size = loopuidstack_size(&my_stack);
    extrae_type_t *types = (extrae_type_t *) malloc(sizeof(extrae_type_t)*size);
    extrae_value_t *values = (extrae_value_t *) malloc(sizeof(extrae_value_t)*size);

    for (int i=0; i<size; ++i)
    {
        types[i] = EXTRAE_LOOPEVENT+i;
        values[i] = 0;
    }

    Extrae_nevent(size, types, values);

    free(types);
    free(values);
}

void 
helper_loop_entry(unsigned int line, char *file_name)
{
    // Just executed on first entry
    if (!rand_init)
    {
        srand(time(NULL));
        rand_init = TRUE;

        char *env_chance_p = getenv(ENVVAR_CHANCE);
        if (env_chance_p != NULL)
        {
            env_chance = TRUE;
            env_chance_value = atof(env_chance_p);
            printf("It. chance set to: %f\n", env_chance_value);
        }
    }

    unsigned int hash = get_loop_hash(line, file_name);
    Extrae_event(EXTRAE_LOOPEVENT, hash);
    loopuidstack_push(&itercounter_stack, (extrae_value_t) 0);
}

void 
helper_loop_exit()
{
    unsigned int niters = (unsigned int)loopuidstack_pop(&itercounter_stack);
    Extrae_event(EXTRAE_LOOPITERCEVENT, niters);
    Extrae_event(EXTRAE_LOOPEVENT, EXTRAE_EXITEVENT);
}

void 
helper_loop_iter_entry(double chance)
{
    double r = (double)rand() / (double)RAND_MAX;
    unsigned int instrument_iter;
    if (!env_chance)
        instrument_iter = (r < chance);
    else
        instrument_iter = (r < env_chance_value);

    loopuid_item* top = loopuidstack_top(&itercounter_stack);
    top->val++;
    if (instrument_iter)
        Extrae_eventandcounters(EXTRAE_ITEREVENT, top->val);
    loopuidstack_push(&decission_stack, (extrae_value_t) instrument_iter);
}

void 
helper_loop_iter_exit()
{
    unsigned int instrument_iter = loopuidstack_pop(&decission_stack);
    if (instrument_iter)
        Extrae_eventandcounters(EXTRAE_ITEREVENT, EXTRAE_EXITEVENT);
}
