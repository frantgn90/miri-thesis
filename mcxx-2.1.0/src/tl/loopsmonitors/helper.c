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

loopuid_stack my_stack = { .top = NULL, .size = 0 };
hashmap_entry_top loopid_hashmap[HASHMAP_SIZE];

unsigned int
get_loop_hash(unsigned int line, char *file_name)
{
    unsigned int hash = 0;
    for(int i=0; i<strlen(file_name); ++i)
    {
        hash ^= file_name[i];
    }
    hash ^= line;
    return hash;
}

unsigned int 
get_loop_uid(unsigned int line, char *file_name)
{
    unsigned int hm_key = line % HASHMAP_SIZE;
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
    new_info->id = last_loop_id++;

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
        (unsigned int line, char * file_name), unsigned int)
unsigned int helper_loopuid_push(unsigned int line, char *file_name)
{
    unsigned int hash = get_loop_hash(line, file_name);
    loopuidstack_push(&my_stack, (extrae_value_t)hash);
    return hash;
}

INTERFACE_ALIASES_F(helper_loopuid_pop,(),extrae_value_t)
extrae_value_t helper_loopuid_pop()
{
    return loopuidstack_pop(&my_stack);
}

INTERFACE_ALIASES_F(helper_loopuid_extrae_entry,(),void)
void helper_loopuid_extrae_entry()
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

INTERFACE_ALIASES_F(helper_loopuid_extrae_exit,(),void)
void helper_loopuid_extrae_exit()
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
