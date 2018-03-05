#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import constants
from utilities import pretty_print
from gui import gui

C_WIDTH = 155
C_NCOLS = 6

FILE_WIDTH = 20
LINE_WIDTH = 4
CODE_WIDTH = 90
TIME_WIDTH = 10
SIZE_WIDTH = 15
EVEN_WIDTH = 10

# https://stackoverflow.com/questions/287871/print-in-terminal-with-colors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class console_gui(gui):
    def __init__(self, pseudocode):
        gui.__init__(self, pseudocode)

        assert(C_NCOLS + FILE_WIDTH + LINE_WIDTH 
                + CODE_WIDTH + TIME_WIDTH + SIZE_WIDTH
                + EVEN_WIDTH == C_WIDTH)

        self.content="+{0}+{1}+{2}+{3}+{4}+{5}+\n".format(
                "-"*FILE_WIDTH,
                "-"*LINE_WIDTH,
                "-"*CODE_WIDTH,
                "-"*TIME_WIDTH,
                "-"*SIZE_WIDTH,
                "-"*EVEN_WIDTH)

        self.content+="|{0:^{6}.{6}}|{1:^{7}.{7}}|{2:^{8}.{8}}"\
                "|{3:^{9}.{9}}|{4:^{10}.{10}}|{5:^{11}.{11}}|\n".format(
                    "FILE",
                    "LINE",
                    "PSEUDOCODE",
                    "E(TIME)",
                    "E(SIZE)",
                    "E(IPC)",
                    FILE_WIDTH,
                    LINE_WIDTH,
                    CODE_WIDTH,
                    TIME_WIDTH,
                    SIZE_WIDTH,
                    EVEN_WIDTH)

        self.content+="+{0}+{1}+{2}+{3}+{4}+{5}+\n".format(
                "-"*FILE_WIDTH,
                "-"*LINE_WIDTH,
                "-"*CODE_WIDTH,
                "-"*TIME_WIDTH,
                "-"*SIZE_WIDTH,
                "-"*EVEN_WIDTH)

        for line in self.pseudocode:
            self.content += str(line) + "\n"

        self.content+="+{0}+{1}+{2}+{3}+{4}+{5}+\n".format(
                "-"*FILE_WIDTH,
                "-"*LINE_WIDTH,
                "-"*CODE_WIDTH,
                "-"*TIME_WIDTH,
                "-"*SIZE_WIDTH,
                "-"*EVEN_WIDTH)

        #self.content+="|{0:^{6}.{6}}|{1:^{7}.{7}}|{2:^{8}.{8}}"\
        #        "|{3:^{9}.{9}}|{4:^{10}.{10}}|{5:^{11}.{11}}|\n".format(
        #            "",
        #            "",
        #            "",
        #            "~100%",
        #            "",
        #            "",
        #            FILE_WIDTH,
        #            LINE_WIDTH,
        #            CODE_WIDTH,
        #            TIME_WIDTH,
        #            SIZE_WIDTH,
        #            EVEN_WIDTH)

    def show(self):
        #print pretty_print(self.content, constants.TRACE_NAME)
        print(self.content)

    class console_line(object):
        def __init__(self, deph):
            self.deph = deph
            self.first_col = ""
            self.second_col = ""
            self.third_col = ""
            self.metric_2 = "-"
            self.metric_3 = "-"
            self.metric_4 = "-"

        def get_tabs(self):
            return ": "*self.deph

        def __str__(self):
            res = "|{0:{6}.{6}}|{1:>{7}.{7}}|{2:{8}.{8}}|{3:{9}.{9}}|"\
                    "{4:{10}.{10}}|{5:{11}.{11}}|".format(
                            self.first_col,
                            self.second_col,
                            self.get_tabs()+self.third_col,
                            self.metric_2,
                            self.metric_3,
                            self.metric_4,
                            FILE_WIDTH,
                            LINE_WIDTH,
                            CODE_WIDTH,
                            TIME_WIDTH,
                            SIZE_WIDTH,
                            EVEN_WIDTH)
            return res

    class console_for(console_line):
        def __init__(self, iterations, misc, deph):
            super(console_gui.console_for, self).__init__(deph)
            self.iterations = iterations
            self.first_col = ""
            self.second_col = " "
            self.third_col = "FOR 1 TO {0} [id={1}]".format(
                    self.iterations,
                    str(misc))
            #self.third_col = "FOR 1 TO {0}".format(
            #        self.iterations)
            self.metric = ""

    class console_for_end(console_line):
        def __init__(self, iterations, deph):
            super(console_gui.console_for_end, self).__init__(deph)
            self.iterations = iterations
            self.first_col = ""
            self.second_col = " "
            self.third_col = "END LOOP"
            self.metric = ""

    class console_call(console_line):
        def __init__(self, call, deph, show_ranks):
            super(console_gui.console_call, self).__init__(deph)
            self.call = call

            self.first_col = self.call.call_file
            self.second_col = str(self.call.line)

            if self.call.print_call_name:
                self.third_col = "{0}()".format(self.call.call)

            if self.call.mpi_call:
                if not self.call.mpi_call_coll:
                    partners = self.parse_partners(
                            self.call.my_callstack.compacted_partner,
                            show_ranks)
                    self.third_col = "{0}({1})".format(self.call.call, partners)

                my_callstack = self.call.my_callstack
                my_loop = self.call.my_callstack.my_loop
                ratio = my_callstack.repetitions[my_callstack.rank]\
                        / float(my_loop.original_iterations)

                if ratio < 1:
                    self.third_col += (" [{0}]".format(round(ratio,2)))

                ''' Showing metrics '''
                metrics_dict = self.call.my_callstack.metrics
                intersection = set(self.call.my_callstack.compacted_ranks)\
                        .intersection(show_ranks)
                if intersection == set(self.call.my_callstack.compacted_ranks):
                    ''' show global values '''
                    metric_2 = metrics_dict["global_mpi_duration_merged_mean"]
                    metric_3 = metrics_dict["global_mpi_msg_size_merged_mean"]
                    metric_4 = metrics_dict["global_42000050_merged_mean"]\
                        / float(metrics_dict["global_42000059_merged_mean"])
                else:
                    ''' just metrics for show_ranks '''
                    metric_2 = 0
                    metric_3 = 0
                    metric_4 = 0
                    cnt = 0
                    for rank in show_ranks:
                        if not rank in metrics_dict: continue
                        metric_2 += metrics_dict[rank]["mpi_duration_merged_mean"]
                        metric_3 += metrics_dict[rank]["mpi_msg_size_merged_mean"]
                        metric_4 += metrics_dict[rank]["42000050_merged_mean"]\
                                /metrics_dict[rank]["42000059_merged_mean"]
                        cnt += 1
                    metric_2 /= cnt
                    metric_3 /= cnt
                    metric_4 /= cnt

                msg_size_unit = ["B","KB","MB","GB"]
                if self.call.mpi_call_coll:
                    self.third_col = "{0}(CommId:{1})".format(self.call.call,
                            metrics_dict["global_50100004_merged_mean"])
                    msg_size_send = metrics_dict["global_50100001_merged_mean"]
                    msg_size_recv = metrics_dict["global_50100002_merged_mean"]
                    
                    if msg_size_send == 0 and msg_size_recv == 0:
                        metric_3 = "-"
                    else:
                        msg_size_coll_send_unit_i=0
                        msg_size_coll_recv_unit_i=0
                        while msg_size_send >= 1000: 
                            msg_size_send/=1000
                            msg_size_coll_send_unit_i+=1

                        while msg_size_recv >= 1000:
                            msg_size_recv/=1000
                            msg_size_coll_recv_unit_i+=1

                        self.metric_3 = "{0}{2}/{1}{3}".format(
                                round(msg_size_send, 2),
                                round(msg_size_recv, 2), 
                                msg_size_unit[msg_size_coll_send_unit_i],
                                msg_size_unit[msg_size_coll_recv_unit_i])

                else:
                    if metric_3 == 0:
                        self.metric_3 = "-"
                    else:
                        msg_size_unit_i=0
                        while metric_3 > 1024:
                            metric_3/=1024
                            msg_size_unit_i+=1

                        self.metric_3 = str(round(metric_3,2))\
                            + msg_size_unit[msg_size_unit_i]

                time_unit_i = 0
                time_unit = ["ns", "us", "ms", "s"]
                while metric_2 >= 1000:
                    metric_2 /= 1000
                    time_unit_i += 1

                self.metric_2 = str(round(metric_2,2)) + time_unit[time_unit_i]
                self.metric_4 = str(round(metric_4,2))
            else:
                self.metric = ""

            if (len(self.call.my_callstack.loop_info) > 0 
                    and self.call.mpi_call):
                self.third_col = "{0} - {1}".format(
                        self.third_col, self.call.my_callstack.loop_info)

        def parse_partners(self, partners, show_ranks):
            res = ""
            for pr in partners:
                from_rank = pr[0]
                to_rank = pr[1]

                if -1 in to_rank: continue
                if from_rank in show_ranks:
                    res += "{0}:{1},".format(from_rank, ",".join(map(str,to_rank)))

            return res[:-1]

    class console_computation(console_line):
        def __init__(self, call, deph, show_ranks):
            super(console_gui.console_computation, self).__init__(deph)
            assert call.mpi_call

            self.call = call

            self.first_col = self.call.call_file
            self.second_col = str(self.call.line)
            self.third_col = "[~ computation ~]"

            burst_metrics = self.call.my_callstack.burst_metrics
            intersection = set(self.call.my_callstack.compacted_ranks)\
                        .intersection(show_ranks)
            if intersection == set(self.call.my_callstack.compacted_ranks):
                ''' show global values '''
                metric_2 = burst_metrics["global_burst_duration_merged_mean"]
                metric_4 = burst_metrics["global_42000050_merged_mean"]\
                        /float(burst_metrics["global_42000059_merged_mean"])
            else:
                ''' just metrics for show_ranks '''
                metric_2 = 0
                metric_4 = 0
                cnt = 0
                for rank in show_ranks:
                    if not rank in burst_metrics: continue
                    metric_2 += burst_metrics[rank]["burst_duration_merged_mean"]
                    metric_4 += burst_metrics[rank]["42000050_merged_mean"]\
                            /burst_metrics[rank]["42000059_merged_mean"]
                    cnt += 1
                metric_2 /= cnt
                metric_4 /= cnt

            self.burst_duration = metric_2
            time_unit_i = 0
            time_unit = ["ns", "us", "ms", "s"]
            while metric_2 >= 1000:
                metric_2 /= 1000
                time_unit_i += 1

            self.metric_2 = str(round(metric_2,2)) + time_unit[time_unit_i]
            self.metric_4 = str(round(metric_4,2))

            self.metric_3 = "-"

    class console_condition(console_line):
        def __init__(self, ranks, el, eli, deph):
            super(console_gui.console_condition,self).__init__(deph)
            self.ranks = ranks
            self.el = el
            self.eli = eli

            self.first_col = ""
            self.second_col = " "
            if self.el:
                self.third_col = "ELSE"
            elif self.eli:
                self.third_col = "ELIF rank in {0}".format(self.ranks)
            else:
                ranks = map(lambda x: str(x), list(self.ranks))
                self.third_col = "IF rank in [{0}]".format(",".join(ranks))
            self.metric = ""

    @classmethod
    def get_pseudo_line(cls):
        return cls.console_line

    @classmethod
    def get_pseudo_for(cls):
        return cls.console_for

    @classmethod
    def get_pseudo_for_end(cls):
        return cls.console_for_end

    @classmethod
    def get_pseudo_call(cls):
        return cls.console_call

    @classmethod
    def get_pseudo_condition(cls):
        return cls.console_condition
    
    @classmethod
    def get_pseudo_computation(cls):
        return cls.console_computation



