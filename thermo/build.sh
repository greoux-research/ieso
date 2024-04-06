# Gréoux Research - www.greoux.re

rm -rf *.o *.bin

g++ -fPIC -Wall -c *.cpp

g++ -fPIC -Wall iesoH2O.o Cogen.o sim.o -lm -o sim.bin
