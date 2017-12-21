#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import constants
from utilities import pretty_print
from gui import gui


class html_gui(gui):
    def __init__(self, pseudocode):
        gui.__init__(self, pseudocode)
        self.content=""

    def show(self):
        pass
