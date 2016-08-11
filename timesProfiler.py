#!/usr/bin/env python

import sys
import json

FUNCS_INFO = {}
FUNCS_TIME = {}

def init_structure(function_map):
    fmap = open(function_map, "r")
    FUNCS_INFO = json.load(fmap)

    for k,v in FUNCS_INFO.iteritems():
        FUNCS_TIME.update({
            v["letter"]:{
                "name":v["name"],
                "paraver": k,
                "tmp_init": 0,
                "counter" : 0,
                "times": []
            }
        })

def get_times(function_par):
    ftimes = open(function_par, "r")
    for line in ftimes:
        data = line.split(" ")
        time = int(data[0])
        enter = True if data[1] == ">" else False
        funcl = data[2].replace("\n", "")
							
        if enter:
            # NOTE: Assuming there are no recursivity !!
            assert(FUNCS_TIME[funcl]["tmp_init"] == 0)
            FUNCS_TIME[funcl]["tmp_init"] = time
        else:
            assert(FUNCS_TIME[funcl]["tmp_init"] != 0)
            FUNCS_TIME[funcl]["times"].append(time - FUNCS_TIME[funcl]["tmp_init"])
            FUNCS_TIME[funcl]["tmp_init"] = 0
            FUNCS_TIME[funcl]["counter"] += 1

def main(argc, argv):
    function_map = argv[1]
    function_par = argv[2]

    init_structure(function_map)
    get_times(function_par)

    print json.dumps(FUNCS_TIME, sort_keys=True, indent=4, separators=(',', ': '))
    return 0

if __name__ == "__main__":
    exit(main(len(sys.argv), sys.argv))
