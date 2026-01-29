#!/bin/bash
# calc_add.sh - Add two numbers

if [ $# -ne 2 ]; then
  echo "Usage: calc_add.sh <num1> <num2>"
  exit 1
fi

echo $(( $1 + $2 ))
