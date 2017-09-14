#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from utilities import pretty_print

class gui(object):
    def __init__(self, pseudocode):
        self.pseudocode = pseudocode
        pass


class console_gui(gui):
    def __init__(self, pseudocode):
        gui.__init__(self, pseudocode)
        self.content=""
        for line in self.pseudocode:
            self.content += str(line) + "\n"

    def show(self):
        print pretty_print(self.content, "Pseudocode")


class html_gui(gui):
    def __init__(self, pseudocode):
        gui.__init__(self, pseudocode)
        self.content=""

    def show(self):
        pass
