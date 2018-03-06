/*--------------------------------------------------------------------
  (C) Copyright 2006-2015 Barcelona Supercomputing Center
                          Centro Nacional de Supercomputacion
  
  This file is part of Mercurium C/C++ source-to-source compiler.
  
  See AUTHORS file in the top level directory for information
  regarding developers and contributors.
  
  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 3 of the License, or (at your option) any later version.
  
  Mercurium C/C++ source-to-source compiler is distributed in the hope
  that it will be useful, but WITHOUT ANY WARRANTY; without even the
  implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
  PURPOSE.  See the GNU Lesser General Public License for more
  details.
  
  You should have received a copy of the GNU Lesser General Public
  License along with Mercurium C/C++ source-to-source compiler; if
  not, write to the Free Software Foundation, Inc., 675 Mass Ave,
  Cambridge, MA 02139, USA.
--------------------------------------------------------------------*/

#include <assert.h>
#include <string>
#include <fstream>
#include <iomanip>

#include "loop-visitor.hpp"
#include "tl-nodecl.hpp"
#include "tl-nodecl-utils.hpp"
#include "tl-nodecl-visitor.hpp"
#include "tl-source.hpp"
#include "tl-pragmasupport.hpp"
#include "cxx-driver-utils.h"

// On every new nested level, EXTRAE_LOOPEVENT will be
// increment by one.
#define EXTRAE_LOOPEVENT 99000000
#define EXTRAE_ITEREVENT 99100000
#define EXTRAE_EXITEVENT 0

namespace TL {
    // This is the visitor used by the run method of this new phase
    // Heritage from ExhaustiveVisitor: This class visits all nodes of the
    // tree (representation of source code, output of frontend) in a recursive
    // manner.

    // Helper function 
    void new_unsigned_variable(TL::Scope context, std::string name, 
            unsigned int i)
    {
        // -- tl-omp-base.cpp:3633 --
        TL::Symbol new_symbol = context.new_symbol(name);
        new_symbol.get_internal_symbol()->kind = SK_VARIABLE;
        new_symbol.set_type(TL::Type::get_unsigned_long_long_int_type());
        symbol_entity_specs_set_is_user_declared(
                new_symbol.get_internal_symbol(), 1);

        Source init_value; init_value << i;
        new_symbol.set_value(init_value.parse_expression(context));
        context.insert_symbol(new_symbol);
    }
    
    Nodecl::NodeclBase get_statement_from_pragma(
            const TL::PragmaCustomStatement& construct)
    {
        Nodecl::NodeclBase stmt = construct.get_statements();

        ERROR_CONDITION(!stmt.is<Nodecl::List>(), "Invalid tree", 0);
        stmt = stmt.as<Nodecl::List>().front();

        ERROR_CONDITION(!stmt.is<Nodecl::Context>(), "Invalid tree", 0);
        stmt = stmt.as<Nodecl::Context>().get_in_context();

        ERROR_CONDITION(!stmt.is<Nodecl::List>(), "Invalid tree", 0);
        stmt = stmt.as<Nodecl::List>().front();

        return stmt;
    }

    void PragmaHandler(TL::PragmaCustomStatement node)
    {
        // -- tl-omp-base-hlt.cpp:9
        Nodecl::NodeclBase loop = get_statement_from_pragma(node);
        std::cout << loop.get_locus_str() << std::endl;
    }

    class ExtraeLoopsVisitor : public Nodecl::ExhaustiveVisitor<void>
    {
        private:
            std::string _nesting_level_var;
            bool _instrument_iterations;
            bool _instrument_only_mpi;
            double _instrument_iterations_chance;
        public:
            ExtraeLoopsVisitor(
                    bool instrument_iterations,
                    double instrument_iterations_chance,
                    bool instrument_only_mpi)
            {
                this->_instrument_iterations = instrument_iterations;
                this->_instrument_iterations_chance = instrument_iterations_chance;
                this->_instrument_only_mpi = instrument_only_mpi;
            }
            void loop_visit_entry(bool entry, Nodecl::NodeclBase node)
            {
                Nodecl::ForStatement node_for;
                Nodecl::WhileStatement node_while;
                bool is_while = false;
                bool is_for = false;

                if (node.is<Nodecl::ForStatement>())
                {
                    is_for = true;
                    node_for = node.as<Nodecl::ForStatement>();
                }
                else if (node.is<Nodecl::WhileStatement>())
                {
                    is_while = true;
                    node_while = node.as<Nodecl::WhileStatement>();
                }
                else
                {
                    exit(1);
                }

                int line = node.get_line();
                std::string filename = node.get_filename();
                if (entry)
                {
                    loop_visit_pre(node, is_while, node_while, is_for, node_for,
                            line, filename);
                }
                else
                {
                    loop_visit_post(node, is_while, node_while, is_for, node_for,
                            line, filename);
                }
            }
            void loop_visit_pre(Nodecl::NodeclBase node,
                bool is_while, Nodecl::WhileStatement node_while,
                bool is_for, Nodecl::ForStatement node_for,
                int line, std::string filename
                )
            {
                /*
                 * W/o taking into account the loop-deph, all loops will have 
                 * the same event_id. In order to see it correctly on Paraver 
                 * you should use the Stacked on Semantic>Compose
                 */
                Source src_loop_init;
                Source src_loop_fini;

                if (this->_instrument_only_mpi)
                {
                    src_loop_init
                        << "helper_loopuid_push(" << line 
                        <<     ",\"" << filename << "\");";
                    src_loop_fini 
                        << "helper_loopuid_pop();";
                }
                else
                {
                    src_loop_init 
                        << "helper_loop_entry(" << line
                        <<     ",\"" << filename << "\");";
                    src_loop_fini 
                        << "helper_loop_exit();";
                }

                FORTRAN_LANGUAGE()
                {
                    Source::source_language = SourceLanguage::C;
                }

                Nodecl::NodeclBase node_loop_init =  
                    src_loop_init.parse_statement(node);
                Nodecl::NodeclBase node_loop_fini = 
                    src_loop_fini.parse_statement(node);

                FORTRAN_LANGUAGE()
                {
                    Source::source_language = SourceLanguage::Current;
                }

                node.prepend_sibling(node_loop_init);
                node.append_sibling(node_loop_fini);
            }

            void loop_visit_post(Nodecl::NodeclBase node,
                bool is_while, Nodecl::WhileStatement node_while,
                bool is_for,   Nodecl::ForStatement node_for,
                int line, std::string filename)
            {
                if (this->_instrument_iterations)
                {

                    //TL::ForStatement for_statement(node);
                    //TL::Symbol ind_var = for_statement.get_induction_variable();
                    //std::string ind_var_name = ind_var.get_name();
                    
                    std::string new_it_var_name = 
                        std::string("__mercurium_it_id_") 
                        + std::to_string(line) + "_" + filename;

                    new_unsigned_variable(node.retrieve_context(), 
                            new_it_var_name, 0);

                    Nodecl::NodeclBase new_statement;
                    Source src;
                    src
                        << "{"
                        <<      "helper_loop_iter_entry("
                        <<          std::to_string(this->
                                _instrument_iterations_chance )
                        <<      ");"
                        <<      statement_placeholder(new_statement)
                        <<      "helper_loop_iter_exit();"
                        << "}";

                    // TODO: There is any superclass that contains all loop 
                    // statements?

                    FORTRAN_LANGUAGE()
                    {
                        Source::source_language = SourceLanguage::C;
                    }

                    Nodecl::NodeclBase generated_code = src.parse_statement(node);

                    FORTRAN_LANGUAGE()
                    {
                        Source::source_language = SourceLanguage::Current;
                    }

                    if (is_for)
                    {
                        new_statement.replace(node_for.get_statement());
                        node_for.get_statement().replace(generated_code);
                    }
                    else if (is_while)
                    {
                        new_statement.replace(node_while.get_statement());
                        node_while.get_statement().replace(generated_code);
                    }
                }
            }

            void mpi_call_visit_pre(const Nodecl::FunctionCall node, 
                    std::string fname)
            {
                //std::cout << "MPI Detected: " << fname << std::endl;
                Source src_mpi_init;
                Source src_mpi_fini;

                src_mpi_init << "helper_loopuid_stack_extrae_entry();";
                src_mpi_fini << "helper_loopuid_stack_extrae_exit();";

                FORTRAN_LANGUAGE()
                {
                    Source::source_language = SourceLanguage::C;
                }

                Nodecl::NodeclBase node_mpi_init =  
                    src_mpi_init.parse_statement(node);
                Nodecl::NodeclBase node_mpi_fini = 
                    src_mpi_fini.parse_statement(node);

                FORTRAN_LANGUAGE()
                {
                    Source::source_language = SourceLanguage::Current;
                }

                node.prepend_sibling(node_mpi_init);
                node.append_sibling(node_mpi_fini);
            }

            virtual void visit_pre(const Nodecl::WhileStatement &node)
            {
                this->loop_visit_entry(true, node.as<Nodecl::NodeclBase>());
            }
            virtual void visit_pre(const Nodecl::ForStatement &node)
            {
                this->loop_visit_entry(true, node.as<Nodecl::NodeclBase>());
            }
            virtual void visit_post(const Nodecl::WhileStatement &node)
            {
                this->loop_visit_entry(false, node.as<Nodecl::NodeclBase>());
            }
            virtual void visit_post(const Nodecl::ForStatement &node)
            {
                this->loop_visit_entry(false, node.as<Nodecl::NodeclBase>());
            }
            virtual void visit_pre(const Nodecl::FunctionCall &node)
            {
                if (this->_instrument_only_mpi)
                {
                    Symbol func = node.get_called().get_symbol();

                    if (func != NULL)
                    {
                        std::string fname = func.get_name();
                        bool mpi_call = (fname.find("MPI_") != std::string::npos 
                            or fname.find("mpi_") != std::string::npos);

                        /*
                         * Maintain this entry point as simple as possible just
                         * in case more functions management is needed in 
                         * the future.
                         */
                        if (mpi_call)
                            this->mpi_call_visit_pre(node, fname);
                    }
                }
            }
    };

    VisitorLoopPhase::VisitorLoopPhase()
    {
        set_phase_name("Loop visitor");
        set_phase_description("This phase shows information about loops");

        register_parameter("all_loops",
                "If this parameter is set all loops will be instrumented. If not" \
                " just those loops with #pragma extrae loop(nesting-deph)",
                _instrument_all_loops_str,
                "0")
            .connect(
                std::bind(&VisitorLoopPhase::set_all_loops_instrumentation,
                    this, std::placeholders::_1));

        register_parameter("only_mpi",
                "If this parameter is set information about loops boundaries "\
                "replaced by events just before and after MPI calls indicating"\
                "to what loops every MPI call belongs to.",
                _instrument_only_mpi_str,
                "0")
            .connect(
                std::bind(&VisitorLoopPhase::set_only_mpi_instrumentation,
                    this, std::placeholders::_1));

        register_parameter("with_iters",
                "Wether iterations will be instrumented or just loops, in that"\
                " case the value indicates the chance of an iteration to be"\
                " instrumented",
                _instrument_iterations_str,
                "0")
            .connect(
                std::bind(&VisitorLoopPhase::set_with_instr_iters,
                    this, std::placeholders::_1));
    }
    VisitorLoopPhase::~VisitorLoopPhase()
    {
    }
    void VisitorLoopPhase::set_with_instr_iters(const std::string& str)
    {
        this->_instrument_iterations_chance = std::stod(str);
        this->_instrument_iterations = (this->_instrument_iterations_chance > 0);
    }
    void VisitorLoopPhase::set_all_loops_instrumentation(const std::string& str)
    {
        parse_boolean_option("all_loops",
                str, _instrument_all_loops, "Assuming true");
    }
    void VisitorLoopPhase::set_only_mpi_instrumentation(const std::string& str)
    {
        parse_boolean_option("only_mpi",
                str, _instrument_only_mpi, "Assuming true");
    }
    void VisitorLoopPhase::run(TL::DTO& dto)
    {
        Nodecl::NodeclBase top_level = 
            *std::static_pointer_cast<Nodecl::NodeclBase>(dto["nodecl"]);

        if (this->_instrument_only_mpi || this->_instrument_iterations)
            this->_instrument_all_loops = true;

        //std::cout << "----- Params -----" << std::endl;
        //std::cout << "- with_iters:" << this->_instrument_iterations 
        //    << std::endl;
        //std::cout << "--- chance  :" << this->_instrument_iterations_chance 
        //    << std::endl;
        //std::cout << "- all_loops :" << this->_instrument_all_loops 
        //    << std::endl;
        //std::cout << "- only_mpi  :" << this->_instrument_only_mpi << std::endl;
        //std::cout << "------------------" << std::endl;

        this->load_headers(top_level);

        /* With no pragmas */
        if (this->_instrument_all_loops)
        {
            ExtraeLoopsVisitor loops_visitor(
                    this->_instrument_iterations,
                    this->_instrument_iterations_chance,
                    this->_instrument_only_mpi);
            loops_visitor.walk(top_level);
        }
        else
        {
            // TODO: is not working at all
            assert(false);

            /* Register #pragma extrae loop */
            register_new_directive(CURRENT_CONFIGURATION,
                    "extrae", "loop", 0,0);

            /* Handler for pragma extrae loop */
            PragmaMapDispatcher map_dispatcher;
            map_dispatcher["extrae"].statement.pre["loop"]
                .connect(std::bind(&PragmaHandler,std::placeholders::_1));

            PragmaVisitor pragma_visitor(map_dispatcher, true);
            pragma_visitor.walk(top_level);
        }
    }

    Nodecl::NodeclBase VisitorLoopPhase::load_headers(Nodecl::NodeclBase top_level)
    {
        if (!IS_FORTRAN_LANGUAGE)
            return top_level;

        const char** old_preprocessor_options = 
            CURRENT_CONFIGURATION->preprocessor_options;

        int num_orig_args = count_null_ended_array(
                (void**)old_preprocessor_options);
        int num_args = num_orig_args;

        // -x c
        num_args += 2;

        // NULL ended
        num_args += 1;

        const char** preprocessor_options = new const char*[num_args];
        for (int i = 0;  i < num_orig_args; i++)
        {
            preprocessor_options[i] = old_preprocessor_options[i];
        }

        // We add -x c since we want /dev/null be preprocessed as an empty C file
        // FIXME - This is very gcc specific
        preprocessor_options[num_args - 3] = "-x";
        preprocessor_options[num_args - 2] = "c";
        preprocessor_options[num_args - 1] = NULL;

        CURRENT_CONFIGURATION->preprocessor_options = preprocessor_options;

        const char* output_filename = preprocess_file("/dev/null");
        delete[] preprocessor_options;

        // Restore old flags
        CURRENT_CONFIGURATION->preprocessor_options = old_preprocessor_options;

        TL::Source src;

        std::ifstream preproc_file(output_filename);

        if (preproc_file.is_open())
        {
            std::string str;

            while (preproc_file.good())
            {
                std::getline(preproc_file, str);
                src << str << "\n";
            }
            preproc_file.close();
        }
        else
        {
            fatal_error("Could not open Nanos++ include");
        }

        Source::source_language = SourceLanguage::C;
        Nodecl::NodeclBase new_tree = src.parse_global(top_level);
        new_tree = Nodecl::TopLevel::make(new_tree);
        Source::source_language = SourceLanguage::Current;

        return new_tree;
    }
}

EXPORT_PHASE(TL::VisitorLoopPhase);
