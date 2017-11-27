#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import cmd, sys, subprocess, os, signal, tempfile, time
import constants

class ParaverInterface(object):
        
    def __init__(self, trace):
        self.trace = trace
        self.paraver_command = ["wxparaver", self.trace]
        self.paraver_process = None
        self.silent_stdout = open(os.devnull, "w")
        self.sigfile = "{0}/paraload.sig".format(os.getenv("HOME"))


    def generate_sigfile(self, from_time, to_time, cfg):
        if os.path.isfile(self.sigfile):
            os.remove(self.sigfile)

        with open(self.sigfile, "w") as f:
            f.write("{0}\n{1}:{2}\n".format(cfg, from_time, to_time))

    def send_signal(self):
        print signal.SIGUSR1
        #os.kill(self.paraver_pid, signal.SIGUSR1)
        command = ["kill","-SIGUSR1","--",str(self.paraver_pid)]
        print " ".join(command)
        #subprocess.Popen(command)

    def run_paraver(self):
        if self.paraver_process is None:
            pid_filename = tempfile.mkstemp()
            pid_file = open(pid_filename[1],"w")

            # Just need a little workarround in wxparaver script
            # Add $! at the end of last line in order to print the PID by means
            # of the stdout
            self.paraver_process = subprocess.Popen(
                    self.paraver_command, 
                    stdout=pid_file,
                    stderr=self.silent_stdout)
    
            self.paraver_process.wait()
            pid_file.close()
 
            self.paraver_pid = ""
            while self.paraver_pid == "":
                pid_file = open(pid_filename[1],"r")
                self.paraver_pid = pid_file.read()
                pid_file.close()

            self.paraver_pid = int(self.paraver_pid)
            print "Running paraver PID={0}".format(self.paraver_pid)

    def zoom(self, from_time, to_time, cfg):
        self.run_paraver()
        self.generate_sigfile(from_time, to_time, cfg)
        self.send_signal()



class sdshell(cmd.Cmd):
    intro  = '\n'
    intro += 'Welcome to structure detection tool interactive shell\n'
    intro += 'Barcelona Supercomputing Center - Centro nacional de Supercomputacion\n'
    intro += 'Performance tools team - tools@bsc.es'
    intro += '\n'
    prompt = '\033[94m(struct_detection)\033[0m> '

    paraver_int = None

    def set_trace(self, trace):
        self.trace = trace

    def set_pseudocode(self, pc):
        self.pc = pc
        
    def get_clustering_thread(self, clustering_thread):
        self.clustering_thread = clustering_thread

    def do_paraver(self, args):
        args = parse(args)
        option = args[0]
        option_args = args[1:]

        if self.paraver_int is None:
            self.paraver_int = ParaverInterface(self.trace)
            self.paraver_int.run_paraver()

        if option == "cut":
            print "Not developed"
        elif option == "show":
            loop_id = option_args[0]
            iteration = option_args[1]
            self.paraver_int.zoom(100000,150000,
                    "/home/jmartinez/BSC/software/paraver/cfgs/mpi/views/MPI_call.cfg")
        else:
            print "{0} does not exist".format(option)

    def do_show(self, args):
        args = parse(args)
        option = args[0]
        option_args = args[1:]

        if option == "pseudocode":
            if "only-mpi" in option_args:
                if self.pc.only_mpi == False:
                    self.pc.only_mpi = True
                    self.pc.generate()
            elif "with-burst-info" in option_args:
                gen = False
                if self.pc.show_burst_info == False:
                    gen = True
                    self.pc.show_burst_info = True
                if self.pc.only_mpi == True:
                    gen = True
                    self.pc.only_mpi = False
                if gen:
                    self.pc.generate()
            elif "default" in option_args:
                gen = False
                if self.pc.show_burst_info == True:
                    gen = True
                    self.pc.show_burst_info = False
                elif self.pc.only_mpi == True:
                    gen = True
                    self.pc.only_mpi = False
                if gen:
                    self.pc.generate()
            self.pc.gui.show()
        elif option == "clustering":
            self.clustering_thread.start()
        elif option == "plot":
            pass

    def do_quit(self, args):
        return True
    def do_q(self, args):
        return True

    def help_paraver(self):
        print "Paraver commands"

    def help_quit(self):
        print "Just finnish program"
    
def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return arg.split()

