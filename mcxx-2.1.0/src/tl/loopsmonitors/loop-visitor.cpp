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

#include "loop-visitor.hpp"
#include "tl-nodecl.hpp"
#include "tl-nodecl-utils.hpp"
#include "tl-nodecl-visitor.hpp"
#include "tl-source.hpp"
#include "tl-pragmasupport.hpp"


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
            std::string _extrae_api_call;
            std::string _nesting_level_var;
            bool _instrument_iterations;
        public:
            ExtraeLoopsVisitor(std::string extrae_api_call,
                    std::string nesting_level_var,
                    bool instrument_iterations)
            {
                this->_extrae_api_call = extrae_api_call;
                this->_nesting_level_var = nesting_level_var;
                this->_instrument_iterations = instrument_iterations;
            }
            void loop_visit_pre(Nodecl::NodeclBase node)
            {
#if 0
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
#endif

                /* 
                 * It can be the loop-id for the moment.
                 * ALERT: Two loops from different files can have the same line
                 */
                unsigned int loop_id = node.get_line();

                                
                /*
                 * W/o taking into account the loop-deph, all loops will have 
                 * the same event_id. In order to see it correctly on Paraver 
                 * you should use the Stacked on Semantic>Compose
                 */
                Source src_loop_init;
                Source src_loop_fini;
                src_loop_init 
                    <<      this->_extrae_api_call << "("
                    <<          EXTRAE_LOOPEVENT
                    <<          ", " << std::to_string(loop_id) << ")";
                
                FORTRAN_LANGUAGE()
                {
                    src_loop_init << ";";
                }
                src_loop_fini 
                    <<      this->_extrae_api_call << "("
                    <<          EXTRAE_LOOPEVENT
                    <<          ", " << EXTRAE_EXITEVENT << ")";
                
                C_LANGUAGE()
                {
                    src_loop_fini << ";";
                }

                C_LANGUAGE()
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

            void loop_visit_post(Nodecl::NodeclBase node)
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

                //TL::ForStatement for_statement(node);
                //TL::Symbol ind_var = for_statement.get_induction_variable();
                //std::string ind_var_name = ind_var.get_name();
                
                if (this->_instrument_iterations)
                {
                    unsigned int loop_id = node.get_line();

                    std::string new_it_var_name = std::string("__mercurium_it_id_")
                        + std::to_string(loop_id);

                    new_unsigned_variable(node.retrieve_context(), 
                            new_it_var_name, 0);

                    Nodecl::NodeclBase new_statement;
                    Source src;
                    src
                        << "{"
                        <<      this->_extrae_api_call << "("
                        <<          EXTRAE_ITEREVENT
                        <<          ", ++" << new_it_var_name  << ");"
                        <<      statement_placeholder(new_statement)
                        <<      this->_extrae_api_call << "("
                        <<          EXTRAE_ITEREVENT
                        <<          "," << EXTRAE_EXITEVENT << ");"
                        << "}";

                    Nodecl::NodeclBase generated_code = src.parse_statement(node);
                    if (is_for)
                    {
                        new_statement.replace(node_for);
                        node_for.get_statement().replace(generated_code);
                    }
                    else if (is_while)
                    {
                        new_statement.replace(node_while);
                        node_while.get_statement().replace(generated_code);

                    }
                }
            }

            void mpi_call_visit_pre(const Nodecl::FunctionCall node)
            {
                std::string fname = node.get_called().get_symbol().get_name();
                std::cout << "MPI Detected: " << fname << std::endl;
            }

            virtual void visit_pre(const Nodecl::WhileStatement &node)
            {
                this->loop_visit_pre(node);
            }
            virtual void visit_pre(const Nodecl::ForStatement &node)
            {
                this->loop_visit_pre(node);
            }
            virtual void visit_post(const Nodecl::WhileStatement &node)
            {
                this->loop_visit_post(node);
            }
            virtual void visit_post(const Nodecl::ForStatement &node)
            {
                this->loop_visit_post(node);
            }
            //virtual void visit_pre(const Nodecl::FunctionCall &node)
            //{
            //    std::string fname = node.get_called().get_symbol().get_name();
            //    bool mpi_call = fname.find("MPI_") != std::string::npos;

            //    /*
            //     * Maintain this entry point as simple as possible just
            //     * in case more functions management is needed in 
            //     * the future.
            //     */
            //    if (mpi_call)
            //        this->mpi_call_visit_pre(node);
            //}

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

        register_parameter("with_hwc",
                "WetherExtrae events will also provide hardware counters "\
                "information or not",
                _with_hw_counters_str,
                "0")
            .connect(
                std::bind(&VisitorLoopPhase::set_with_hwc_instrumentation,
                    this, std::placeholders::_1));
        register_parameter("with_iters",
                "Wether iterations will be instrumented or just loops.",
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
        parse_boolean_option("with_iters",
                str, _instrument_iterations, "Assuming true");
    }
    void VisitorLoopPhase::set_all_loops_instrumentation(const std::string& str)
    {
        parse_boolean_option("all_loops",
                str, _instrument_all_loops, "Assuming true");
    }
    void VisitorLoopPhase::set_with_hwc_instrumentation(const std::string& str)
    {
        parse_boolean_option("with_hwc",
                str, _with_hw_counters, "Assuming true");
    }
    void VisitorLoopPhase::run(TL::DTO& dto)
    {
        Nodecl::NodeclBase top_level = 
            *std::static_pointer_cast<Nodecl::NodeclBase>(dto["nodecl"]);

        /* This variable will control the nesting level */
        //new_unsigned_variable(top_level.retrieve_context(),
        //        this->_nesting_level_var, 0);

        FORTRAN_LANGUAGE()
        {
            if (this->_with_hw_counters)
                this->_extrae_api_call = "CALL extrae_eventandcounters";
            else
                this->_extrae_api_call = "CALL extrae_event";
        }
        else
        {
            if (this->_with_hw_counters)
                this->_extrae_api_call = "Extrae_eventandcounters";
            else
                this->_extrae_api_call = "Extrae_event";
        }

        if (this->_instrument_all_loops)
        {
            ExtraeLoopsVisitor loops_visitor(
                    this->_extrae_api_call,
                    this->_nesting_level_var,
                    this->_instrument_iterations);
            loops_visitor.walk(top_level);
        }
        else
        {
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
}

EXPORT_PHASE(TL::VisitorLoopPhase);
