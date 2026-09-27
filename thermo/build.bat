rem Gréoux Research - www.greoux.re

del *.o *.bin

g++ -fPIC -Wall -c *.cpp

g++ -fPIC -Wall iesOptimiserH2O.o Cogen.o sim.o -lm -o sim.bin
