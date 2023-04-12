#!/bin/bash

# Start "DynamoDB Local" before running this script.
# Make sure to accept requests on port 8000.
# And the AWS CLI default profile must already be created.
# 
# [Example]
# 1. docker pull amazon/dynamodb-local:latest
# 2. docker run -d --name dynamodb -p 8000:8000 amazon/dynamodb-local
# 3. aws configure


SCRIPT_PATH="${BASH_SOURCE:-$0}"
ABS_SCRIPT_PATH="$(realpath "${SCRIPT_PATH}")"
SCRIPTDIR=$(dirname "${ABS_SCRIPT_PATH}")
ENV_FILE="$SCRIPTDIR/../.env"

if [ -f "$ENV_FILE" ]; then
  while read -r line; do
    export "${line?}"
  done < "$ENV_FILE"
fi
export AWS_PROFILE=default  # required for DynamoDB Local

python3 -m unittest
