#!/bin/bash

SCRIPT_PATH="${BASH_SOURCE:-$0}"
ABS_SCRIPT_PATH="$(realpath "${SCRIPT_PATH}")"
SCRIPTDIR=$(dirname "${ABS_SCRIPT_PATH}")
ENV_FILE="$SCRIPTDIR/.env"

if [ -f "$ENV_FILE" ]; then
  while read -r line; do
    line_first_ch="${line:0:1}"
    if [ "${line_first_ch}" != "#" ]; then
      export "${line?}"
    fi
  done < "$ENV_FILE"
fi

if [ -z "$AWS_REGION" ]; then
  AWS_REGION=ap-northeast-1
fi

if [ -z "$AWS_PROFILE" ]; then
  AWS_PROFILE=default
fi

sam build --parameter-overrides "WebhookDockerTag=$WEBHOOK_DOCKER_TAG ProcessorDockerTag=$PROCESSOR_DOCKER_TAG"
