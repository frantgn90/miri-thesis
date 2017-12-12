#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import cmd, sys, subprocess, os, signal, tempfile, time
import constants

class ParaverInterface(object):
        
    def __init__(self, trace):
        self.trace = os.path.abspath(trace)
        self.paraver_command = ["wxparaver"]
        self.paraver_process = None
        self.paraver_pid = 0
        self.silent_stdout = open(os.devnull, "w")
        self.sigfile = "{0}/paraload.sig".format(os.getenv("HOME"))


    def generate_sigfile(self, from_time, to_time, cfg):
        if os.path.isfile(self.sigfile):
            os.remove(self.sigfile)

        with open(self.sigfile, "w") as f:
            f.write("{0}\n{1}:{2}\n{3}\n".format(cfg, from_time, to_time,
                self.trace))

    def run_paraver(self):
        if self.check_process() == False:
            pid_filename = tempfile.mkstemp()
            pid_file = open(pid_filename[1],"w")

            # Just need a little workarround in wxparaver script
            # Add $! at the end of last line in order to print the PID by means
            # of the stdout
            self.paraver_process = subprocess.Popen(
                    self.paraver_command, 
                    stdout=pid_file,
                    stderr=self.silent_stdout)
    
            #self.paraver_process.wait()
            pid_file.close()
 
            self.paraver_pid = ""
            while self.paraver_pid == "":
                pid_file = open(pid_filename[1],"r")
                self.paraver_pid = pid_file.read()
                pid_file.close()

            self.paraver_pid = int(self.paraver_pid)
            print "Running paraver PID={0}".format(self.paraver_pid)

    def close(self):
        if self.check_process() == True:
            os.kill(self.paraver_pid, signal.SIGKILL)

    def check_process(self):
        if self.paraver_pid == 0:
            return False
        else:
            try:
                os.kill(self.paraver_pid, 0)
            except OSError:
                return False
            else:
                return True

    def zoom(self, from_time, to_time, cfg):
        self.run_paraver()
        self.generate_sigfile(from_time, to_time, cfg)
        time.sleep(0.5)
        os.kill(self.paraver_pid, signal.SIGUSR1)

''' Commands definitions '''

PARAVER_SHOW = "show"

PSEUDOCODE_NO_CS = "wo-cs"
PSEUDOCODE_SHOW_BURST = "w-burst-info"
PSEUDOCODE_BURST_TH = "w-burst-threshold"
PSEUDOCODE_DEFAULT = "default" 
PSEUDOCODE_RANKS_FILTER = "ranks" 

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
        
    def set_clustering_thread(self, clustering_thread):
        self.clustering_thread = clustering_thread

    def do_paraver(self, args):
        args = parse(args)

        if self.paraver_int is None:
            self.paraver_int = ParaverInterface(self.trace)
            self.paraver_int.run_paraver()

        if len(args) == 0:
            return False

        option = args[0]
        option_args = args[1:]

        if option == PARAVER_SHOW:
            loop_id = option_args[0]
            cluster_id = loop_id.split(".")[0]
            iteration = int(option_args[1])
            
            cluster = None
            for cl in self.pc.clusters_set:
                if cl.cluster_id == int(cluster_id):
                    cluster = cl

            if cluster == None:
                print "No cluster with id={0}".format(cluster_id)
                return False

            loop_obj = cluster.get_loop(loop_id)
            if loop_obj == None:
                print "No loop with id={0}".format(loop_id)
                return False

            it_times = loop_obj.get_iteration(iteration)
            if iteration is None:
                return False

            self.paraver_int.zoom(it_times[0], it_times[1],
                    constants.PARAVER_MPI_CFG)
        else:
            print "{0} does not exist".format(option)

    def do_pseudocode(self, args):
        args = parse(args)
        gen = False
        if len(args) == 0: args = ["default"]

        if PSEUDOCODE_NO_CS in args:
            if self.pc.only_mpi == False:
                gen = True
                self.pc.only_mpi = True
        if PSEUDOCODE_SHOW_BURST in args:
            if self.pc.show_burst_info == False:
                gen = True
                self.pc.show_burst_info = True
        if PSEUDOCODE_BURST_TH in args:
            burst_threshold = float(args[args.index(PSEUDOCODE_BURST_TH)+1])
            if self.pc.burst_threshold != burst_threshold:
                gen = True
                self.pc.burst_threshold = burst_threshold
        if PSEUDOCODE_DEFAULT in args:
            if PSEUDOCODE_NO_CS in args or PSEUDOCODE_SHOW_BURST in args:
                print "default should go alone"
                return False

            if self.pc.show_burst_info == True:
                gen = True
                self.pc.show_burst_info = False
            if self.pc.only_mpi == True:
                gen = True
                self.pc.only_mpi = False
        if PSEUDOCODE_RANKS_FILTER in args:
            ranks = map(int,args[args.index(PSEUDOCODE_RANKS_FILTER)+1].split(","))
            if self.pc.show_ranks != ranks:
                gen = True
                self.pc.show_ranks = set(ranks)
        else:
            if self.pc.show_ranks != self.pc.all_ranks:
                gen = True
                self.pc.show_ranks = self.pc.all_ranks

        if gen:
            self.pc.generate()
        self.pc.gui.show()

    def do_clustering(self, args):
        self.clustering_thread.start()

    def do_quit(self, args):
        self.quit()
        return True
    def do_q(self, args):
        self.quit()
        return True

    def quit(self):
        if not self.paraver_int is None:
            self.paraver_int.close()


    def help_paraver(self):
        print "Paraver commands"

    def help_quit(self):
        print "Just finnish program"
    
def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return arg.split()

