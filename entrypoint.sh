#!/bin/bash

# if /reservations.yaml exists then run the python file to generate the dhcpd config.
FILE=/*.yaml
if test -f $FILE; then
    python3.9 /template-generation.py
fi

# allow arguments to be passed to dhcpd
if [[ ${1:0:1} = '-' ]]; then
  EXTRA_ARGS="$@"
  set --
elif [[ ${1} == dhcpd || ${1} == $(which dhcpd) ]]; then
  EXTRA_ARGS="${@:2}"
  set --
fi

# default behaviour is to launch dhcpd with -f and -d options
if [[ -z ${1} ]]; then
  echo "Starting dhcpd..."
  exec $(which dhcpd) -f -d ${EXTRA_ARGS}
else
  exec "$@"
fi
