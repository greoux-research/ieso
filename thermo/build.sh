# Gréoux Research (2024). IES Optimiser: a linear optimiser-based integrated energy system modelling environment. https://github.com/greoux-research/ies-optimiser

rm -rf *.o *.bin

g++ -fPIC -Wall -c *.cpp

g++ -fPIC -Wall iesOptimiserH2O.o Cogen.o sim.o -lm -o sim.bin
