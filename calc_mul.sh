#!/bin/bash
# calc_mul.sh - Multiply two numbers

if [ $# -ne 2 ]; then
  echo "Usage: calc_mul.sh <num1> <num2>"
  exit 1
fi

echo $(( $1 * $2 ))
