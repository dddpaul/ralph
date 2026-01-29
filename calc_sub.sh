#!/bin/bash
# calc_sub.sh - Subtract two numbers

if [ $# -ne 2 ]; then
  echo "Usage: calc_sub.sh <num1> <num2>"
  exit 1
fi

echo $(( $1 - $2 ))
