#!/bin/bash

echo "STDIN:"
cat

echo
echo "ARGS:"
printf '<%s>\n' "$@"

exit 0
