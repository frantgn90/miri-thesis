!
! helper_module.f
! Copyright (C) 2018 Juan Francisco Martínez Vera <juan.martinez[AT]bsc.es>
!
! Distributed under terms of the MIT license.
!
! https://gcc.gnu.org/onlinedocs/gfortran/Interoperable-Subroutines-and-Functions.html#Interoperable-Subroutines-and-Functions
! http://fortranwiki.org/fortran/show/iso_c_binding

      module helper_module
          interface
              function helper_loopuid_push (line,file_name) bind (C)
              use iso_c_binding, only: c_int,c_char
              integer (c_int), VALUE :: line
              character (c_char) :: file_name(*)
              end function helper_loopuid_push
      
              function helper_loopuid_pop() bind(C)
              use iso_c_binding
              end function helper_loopuid_pop 
      
              subroutine helper_loopuid_extrae_entry() bind(C)
              use iso_c_binding
              end subroutine helper_loopuid_extrae_entry
      
              subroutine helper_loopuid_extrae_exit() bind(C)
              use iso_c_binding
              end subroutine helper_loopuid_extrae_exit
          end interface          
      end module helper_module
