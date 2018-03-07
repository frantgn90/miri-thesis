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
unsigned int helper_initialized = FALSE;
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

    while ((c = str[i++]))
        hash = ((hash << 5) + hash) + c; /* hash * 33 + c */

    return hash;
}

unsigned int 
get_loop_uid(unsigned int line, char *file_name)
{

    unsigned int hash = get_loop_hash(line, file_name);
    unsigned int hm_key = hash % HASHMAP_SIZE;
    hashmap_entry_top *hm_entry_top = &loopid_hashmap[hm_key];

    hashmap_entry *item = hm_entry_top->first;
    unsigned int entry_size = hm_entry_top->size;

    for (int i=0; i<entry_size; ++i)
    {
        if (item->info->line == line
                && item->info->file_name == file_name)
        {
            return item->info->id;
        }
        item = item->next;
    }

    loopid_container *new_info = (loopid_container *) 
        malloc(sizeof(loopid_container));
    new_info->line = line;
    new_info->file_name = file_name;
    new_info->id = hash;

    hashmap_entry *new_hm_entry = (hashmap_entry *)
        malloc(sizeof(hashmap_entry));
    new_hm_entry->info = new_info;
    new_hm_entry->next = hm_entry_top->first;

    hm_entry_top->first = new_hm_entry;
    hm_entry_top->size++;

    return new_info->id;
}

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
        snprintf(&res[res_i],char_size+1,"%03llu",iterator->val);
        res[res_i+char_size]=separator;
        iterator = iterator->next;
        res_i+=(char_size+1);
    }
    res[res_i-1]='\0';
    return res;
}

INTERFACE_ALIASES_F(helper_init,(),void)
void helper_init()
{
    // Just executed on first entry
    if (!helper_initialized)
    {
        helper_initialized = TRUE;
        srand(time(NULL));

        char *env_chance_p = getenv(ENVVAR_CHANCE);
        if (env_chance_p != NULL)
        {
            env_chance = TRUE;
            env_chance_value = atof(env_chance_p);
            printf("It. chance set to: %f\n", env_chance_value);
        }

        for (int i=0; i<HASHMAP_SIZE; ++i)
        {
            loopid_hashmap[i].first = NULL;
            loopid_hashmap[i].size = 0;
        }
    }
    else
    {
        printf("[HELPER] Warning: helper_init() called more than one time\n");
    }
}

INTERFACE_ALIASES_F(helper_fini,(),void)
void helper_fini()
{
    unsigned int nvalues = 0;
    extrae_type_t type = EXTRAE_LOOPEVENT;
    extrae_value_t *values;
    char **desc_values;
    for (int i=0; i<HASHMAP_SIZE; ++i)
        nvalues += loopid_hashmap[i].size;

    values = (extrae_value_t *) calloc(nvalues, sizeof(extrae_value_t));
    desc_values = (char **) calloc(nvalues, sizeof(char *));
    for (int i=0; i<nvalues; ++i)
        desc_values[i] = (char *) malloc(50*sizeof(char));

    int nvalues_i = 0;
    for (int i=0; i<HASHMAP_SIZE; ++i)
    {
        unsigned int entry_size = loopid_hashmap[i].size;
        hashmap_entry *item = loopid_hashmap[i].first;
        if (entry_size > 0)
        {
            for (int j=0; j<entry_size; ++j)
            {
                unsigned int line = item->info->line;
                char *file_name = item->info->file_name;
                sprintf(desc_values[nvalues_i], "%s:%d", file_name, line);
                values[nvalues_i] = item->info->id;
                nvalues_i += 1;
                item = item->next;
            }
        }
    }
    Extrae_define_event_type(&type, "Instrumented loops by extraecc/fc", 
            &nvalues, values, desc_values);
}

INTERFACE_ALIASES_F(helper_loopuid_push,
        (unsigned int line, char * file_name), void)
void helper_loopuid_push(unsigned int line, char *file_name)
{
    unsigned int hash = get_loop_uid(line, file_name);
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

INTERFACE_ALIASES_F(helper_loop_entry,(unsigned int line, char *file_name),void)
void helper_loop_entry(unsigned int line, char *file_name)
{
    unsigned int instrument_loop = TRUE;
    if (loopuidstack_size(&decission_stack) > 0)
    {
        instrument_loop = loopuidstack_top(&decission_stack)->val;
    }
    if (instrument_loop)
    {
        unsigned int hash = get_loop_uid(line, file_name);
        Extrae_event(EXTRAE_LOOPEVENT, hash);
        loopuidstack_push(&itercounter_stack, (extrae_value_t) 0);
    }
}

INTERFACE_ALIASES_F(helper_loop_exit,(),void)
void helper_loop_exit()
{
    unsigned int instrument_loop = TRUE;
    if (loopuidstack_size(&decission_stack) > 0)
    {
        instrument_loop = loopuidstack_top(&decission_stack)->val;
    }
    if (instrument_loop)
    {
        unsigned int niters = (unsigned int)loopuidstack_pop(&itercounter_stack);
        Extrae_event(EXTRAE_LOOPITERCEVENT, niters);
        Extrae_event(EXTRAE_LOOPEVENT, EXTRAE_EXITEVENT);
    }
}

INTERFACE_ALIASES_F(helper_loop_iter_entry,(double chance),void)
void helper_loop_iter_entry(double chance)
{
    unsigned int instrument_iter = TRUE;
    unsigned int top_instrument_iter = TRUE;
    double r = (double)rand() / (double)RAND_MAX;

    if (loopuidstack_size(&decission_stack) > 0)
    {
        top_instrument_iter = loopuidstack_top(&decission_stack)->val;
    }

    if (top_instrument_iter)
    {
        if (!env_chance)
            instrument_iter = (r < chance);
        else
            instrument_iter = (r < env_chance_value);

        loopuid_item* top = loopuidstack_top(&itercounter_stack);
        top->val++; 

        if (instrument_iter)
            Extrae_eventandcounters(EXTRAE_ITEREVENT, top->val);
    }
    loopuidstack_push(&decission_stack, 
            (extrae_value_t) instrument_iter&top_instrument_iter);
}

INTERFACE_ALIASES_F(helper_loop_iter_exit,(),void)
void helper_loop_iter_exit()
{
    unsigned int instrument_iter = loopuidstack_pop(&decission_stack);
    if (instrument_iter)
        Extrae_eventandcounters(EXTRAE_ITEREVENT, EXTRAE_EXITEVENT);
}
