#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import cmd, sys

class sdshell(cmd.Cmd):
    intro  = '\n'
    intro += 'Welcome to structure detection tool interactive shell\n'
    intro += 'Barcelona Supercomputing Center - Centro nacional de Supercomputacion\n'
    intro += 'Performance tools team - tools@bsc.es'
    intro += '\n'
    prompt = '\033[94m(struct_detection)\033[0m> '

    def set_gui(self, gui):
        self.gui = gui
        
    def get_clustering_thread(self, clustering_thread):
        self.clustering_thread = clustering_thread

    def do_paraver(self, args):
        args = parse(args)
        option = args[0]
        option_args = args[1:]

        if option == "link":
            pid = int(option_args[0])
            print "Not developed"
        elif option == "cut":
            loop_id = int(option_args[0])
            iteration = int(option_args[1])
            print "Not developed"
        elif option == "show":
            loop_id = int(option_args[0])
            iteration = int(option_args[1])
            print "Not developed"
        else:
            print "{0} does not exist".format(option)

    def do_show(self, args):
        args = parse(args)
        option = args[0]
        option_args = args[1:]

        if option == "pseudocode":
            self.gui.show()
        elif option == "clustering":
            self.clustering_thread.start()


    def do_quit(self, args):
        return True

    def help_paraver(self):
        print "Paraver commands"

    def help_quit(self):
        print "Just finnish program"
    
def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return arg.split()

