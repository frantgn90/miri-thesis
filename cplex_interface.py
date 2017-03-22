#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import os, subprocess
import tempfile

import constants

class CplexInterface(object):

    def __init__(self):
        self.outdir  = tempfile.mkdtemp(prefix="struct-gen.cplex.")
        self.outfile = "{0}/{1}".format(self.outdir, constants.OPL_PROBLEM_OUT)
        self.errfile = "{0}/{1}".format(self.outdir, constants.OPL_PROBLEM_ERR)
        self.infile  = "{0}/{1}".format(self.outdir, 
                constants.OPL_PROBLEM_IN.split("/")[-1])

        self.executed = False

    def set_args(self, args):
        self.deltas = args[constants.OPL_ARG_DELTAS]

        ff = open(self.infile, "w")
        ff.write("{0}={1};\n".format(constants.OPL_ARG_BIGM, args[constants.OPL_ARG_BIGM]))
        ff.write("{0}={1};\n".format(constants.OPL_ARG_NDELTAS, args[constants.OPL_ARG_NDELTAS]))
        ff.write("{0}={1};\n".format(constants.OPL_ARG_NPOINTS, args[constants.OPL_ARG_NPOINTS]))
        ff.write("{0}={1};\n".format(constants.OPL_ARG_DELTAS, args[constants.OPL_ARG_DELTAS]))
        ff.write("{0}={1};\n".format(constants.OPL_ARG_POINTS, args[constants.OPL_ARG_POINTS]))
        ff.write("{0}={1};\n".format(constants.OPL_ARG_DISTDP, args[constants.OPL_ARG_DISTDP]))
        ff.close()

        return self.infile

    def get_errfile(self):
        return self.errfile

    def get_outfile(self):
        return self.outfile

    def set_infile(self, infile):
        assert infile[0] == "/", "CPLEX input file path should be absolute!"

        self.infile = infile
        os.remove(constants.OPL_PROBLEM_IN)
        os.symlink(self.infile, constants.OPL_PROBLEM_IN)
        self.deltas = self.parse_field_from_file(
                constants.OPL_ARG_DELTAS,
                self.infile)

    def run(self):
        assert os.path.isfile(self.infile)

        os.remove(constants.OPL_PROBLEM_IN)
        os.symlink(self.infile, constants.OPL_PROBLEM_IN)

        foutfile = open(self.outfile, "w")
        ferrfile = open(self.errfile, "w")

        subprocess.call([constants.OPL_RUN_SCRIPT],
                stdout=foutfile,
                stderr=ferrfile)

        foutfile.close()
        ferrfile.close()
        self.executed = True

    def get_used_deltas(self):
        assert self.executed, "Problem not yet executed."

        used_deltas = self.parse_field_from_file(
                constants.OPL_USED_DELTA,
                self.outfile)
        result = []

        for used_delta, delta in zip(used_deltas, self.deltas):
            if used_delta:
                result.append(delta)

        return result

    def get_delta_point_map(self, point):
        assert self.executed, "Problem not yet executed."

        delta_point_map = self.parse_field_from_file(
                constants.OPL_POINT_DELTA,
                self.outfile)

        idelta=0
        for delta_map in delta_point_map:
            if delta_map[point] == 1:
                break
            else:
                idelta += 1
        
        return self.deltas[idelta]

    def parse_field_from_file(self, field_name, infile_path):
        assert field_name in [
                constants.OPL_ARG_DELTAS,
                constants.OPL_DELTA_DIST,
                constants.OPL_USED_DELTA, 
                constants.OPL_POINT_DELTA]
        
        with open(infile_path) as infile:
            lines=infile.readlines()

            infield=False
            field_data=""
            for l in lines:
                if "<<<" in l or "//" in l:
                    continue

                l=l.strip()+" "
                if infield == False and not "=" in l:
                    continue

                elif infield == False and "=" in l:
                    equal_index=l.index("=")
                    fieldName=l[:equal_index]
                    fieldName=fieldName.strip()
                    
                    if fieldName == field_name:
                        infield=True
                        l=l.replace(" ", ",")
                        field_data=l[equal_index+1:]

                elif infield == True and "=" not in l:

                    l=l.replace(" ", ",")
                    field_data+=l

                elif infield == True and "=" in l:
                    break

            assert len(field_data) > 0, "{0} @ {1} does not exist"\
                    .format(field_name, infile_path)

            field_data=field_data.replace("\n"," ")
            field_data=field_data.replace(";","")
            field_data=field_data.strip()

            field_data=field_data[field_data.index("["):-field_data[::-1].index("]")]

        return eval(field_data)
