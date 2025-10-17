#!/bin/bash

# Clean up previous output files

rm -rf datasets/*/*ieso*.json

# Find all original JSON input files

json_files=$(find datasets/ -type f -name '*.json')

# Loop through each file and run both cases

for file in $json_files; do

  echo "$(basename "$file")"

  python ieso.py "$file"

  python ieso.py "$file" carbon-constraint=50 non-served-power-constraint=0.05

done
