struct _IO_FILE_plus;
extern struct _IO_FILE_plus _IO_2_1_stdin_;
extern struct _IO_FILE_plus _IO_2_1_stdout_;
extern struct _IO_FILE_plus _IO_2_1_stderr_;
struct _IO_FILE;
extern struct _IO_FILE *stdin;
extern struct _IO_FILE *stdout;
extern struct _IO_FILE *stderr;
extern int sys_nerr;
extern const char *const sys_errlist[];
typedef unsigned int extrae_type_t;
typedef unsigned long long int extrae_value_t;
void Extrae_eventandcounters(extrae_type_t type, extrae_value_t value);
extern int printf(const char *__restrict __format, ...);
int main(int argc, char **argv)
{
  /* << fake context >> { */
  unsigned long long int __mercurium_it_id_12 = 0;
  Extrae_eventandcounters(99000000, 12);
  for (int i = 0; i < 2;  ++i)
    {
      Extrae_eventandcounters(99100000,  ++__mercurium_it_id_12);
      {
        /* << fake context >> { */
        unsigned long long int __mercurium_it_id_14 = 0;
        Extrae_eventandcounters(99000001, 14);
        for (int j = 0; j < 2;  ++j)
          {
            Extrae_eventandcounters(99100001,  ++__mercurium_it_id_14);
            {
              printf("Hola manola!\n");
            }
            Extrae_eventandcounters(99100001, 0);
          }
        Extrae_eventandcounters(99000001, 0);
        /* } << fake context >> */
      }
      Extrae_eventandcounters(99100000, 0);
    }
  Extrae_eventandcounters(99000000, 0);
  /* } << fake context >> */
  /* << fake context >> { */
  unsigned long long int __mercurium_it_id_18 = 0;
  Extrae_eventandcounters(99000000, 18);
  for (int i = 0; i < 2;  ++i)
    {
      Extrae_eventandcounters(99100000,  ++__mercurium_it_id_18);
      {
        printf("Hola manola!\n");
      }
      Extrae_eventandcounters(99100000, 0);
    }
  Extrae_eventandcounters(99000000, 0);
  /* } << fake context >> */
  return 0;
}
