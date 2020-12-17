#!/bin/bash

source $(dirname "${BASH_SOURCE[0]}")/setupenv.sh

verbosity=0
# Stores any extra requirments passed to pip
extras_require=()

optstring=":dhtv"

function usage {
    echo "Usage: ${BASH_SOURCE[0]} [-dhtv]."
    echo -e "\td: build with documentation dependencies"
    echo -e "\th: displays this usage message"
    echo -e "\tt: build with test dependencies"
    echo -e "\tv: verbose mode"
}

while getopts ${optstring} arg; do
    case ${arg} in
        d)
            extras_require+=("doc")
            ;;
        h)
            usage
            exit 0
            ;;
        t)
            extras_require+=("tests")
            ;;
        v)
            verbosity=1
            ;;
        :)
            echo "$0: Must supply an argument to -$OPTARG." >&2
            echo 1
            ;;
        ?)
            echo "Invalid option: -${OPTARG}. Use -h for usage."
            exit 2
            ;;
    esac
done

# Install requirements
python -m pip install --upgrade pip
python -m pip install attrs>=17.4.0 
python -m pip install --upgrade setuptools wheel
if [ -f requirements.txt ]; then
    pip install -r requirements.txt;
fi

# If opts indicate any extra requirments, build a well-formed argument for pip
# e.g. [tests] or [doc,tests]
extras_string=""
i=0
if [ ${#extras_require[@]} -gt 0 ]; then
   extras_string="["
   for extra in "${extras_require[@]}"; do
       if [ $i -gt 0 ] && [ $i -lt "${#extras_require[@]}" ]; then
           extras_string="${extras_string},${extra}"
       else
           extras_string=${extras_string}${extra}
       fi
       i=$((i+1))
   done
   extras_string="${extras_string}]"
fi

#echo $extras_string

# Install xicam with any extra requirements
pip install -e "${GITHUB_WORKSPACE}${extras_string}"

