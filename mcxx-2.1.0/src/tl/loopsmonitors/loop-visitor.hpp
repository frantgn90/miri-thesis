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

#ifndef TL_LOOP_VISITOR_HPP
#define TL_LOOP_VISITOR_HPP

#include "tl-compilerphase.hpp"
#include "tl-pragmasupport.hpp"

namespace TL
{
    // Phase class
    // It defines a new phase of the compilation
    class VisitorLoopPhase : public TL::CompilerPhase
    {
        private:
            std::string _instrument_all_loops_str;
            bool _instrument_all_loops;
            std::string _instrument_only_mpi_str;
            bool _instrument_only_mpi;
            std::string _instrument_iterations_str;
            bool _instrument_iterations;
            double _instrument_iterations_chance;

            std::string _extrae_api_nevent_call;
            std::string _extrae_api_event_call;
        public:
            // The constructor
            // In this method name and description of phase can be
            // set.
            VisitorLoopPhase();
            ~VisitorLoopPhase();

            void set_all_loops_instrumentation(const std::string& str);
            void set_with_hwc_instrumentation(const std::string& str);
            void set_with_instr_iters(const std::string& str);
            void set_only_mpi_instrumentation(const std::string& str);
            Nodecl::NodeclBase load_headers(Nodecl::NodeclBase);

            // Run method is where magics should be done
            virtual void run(TL::DTO& dto);
    };
}

#endif // TL_LOOP_VISITOR_HPP
