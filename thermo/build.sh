# Gréoux Research (2024). IESO: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ieso

rm -rf *.o *.bin

g++ -fPIC -Wall -c *.cpp

g++ -fPIC -Wall iesoH2O.o Cogen.o sim.o -lm -o sim.bin
