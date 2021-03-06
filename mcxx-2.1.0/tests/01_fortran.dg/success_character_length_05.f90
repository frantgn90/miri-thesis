! <testinfo>
! test_generator=config/mercurium-fortran
! </testinfo>
MODULE MOO
    IMPLICIT NONE
CONTAINS
    SUBROUTINE SUB(A, C, PC)
        IMPLICIT NONE
        CHARACTER(LEN=*), ALLOCATABLE :: A
        CHARACTER(LEN=:), ALLOCATABLE :: C
        CHARACTER(LEN=:), POINTER :: PC
    END SUBROUTINE SUB

    SUBROUTINE FOO()
        IMPLICIT NONE

        CHARACTER(LEN=10), ALLOCATABLE :: A
        CHARACTER(LEN=:), ALLOCATABLE :: C
        CHARACTER(LEN=:), POINTER :: PC

        CHARACTER(LEN=100) :: SRC

        ALLOCATE(A)
        ALLOCATE(C, SOURCE=SRC)
        ALLOCATE(C, SOURCE=SRC)
        ALLOCATE(PC, SOURCE=SRC)

        CALL SUB(A, C, PC)
    END SUBROUTINE FOO
END MODULE MOO
