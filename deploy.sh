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

if [ -z "$APP_NAME" ]; then
  echo "[ERROR] Environment variable \"APP_NAME\" is required."
  exit 1
fi

if [ -z "$AWS_REGION" ]; then
  AWS_REGION=ap-northeast-1
fi

if [ -z "$AWS_PROFILE" ]; then
  AWS_PROFILE=default
fi

# Push docker images
WEBHOOK_DOCKER_REPO_NAME=$APP_NAME-$ENVIRONMENT/linebotwebhook
PROCESSOR_DOCKER_REPO_NAME=$APP_NAME-$ENVIRONMENT/linebotprocessor

aws ecr create-repository --repository-name "$WEBHOOK_DOCKER_REPO_NAME" --image-tag-mutability MUTABLE
aws ecr create-repository --repository-name "$PROCESSOR_DOCKER_REPO_NAME" --image-tag-mutability MUTABLE

aws ecr get-login-password --region "${AWS_REGION}" --profile "$AWS_PROFILE" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker tag "linebotwebhook:$WEBHOOK_DOCKER_TAG" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$WEBHOOK_DOCKER_REPO_NAME:$WEBHOOK_DOCKER_TAG"
docker tag "linebotprocessor:$PROCESSOR_DOCKER_TAG" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROCESSOR_DOCKER_REPO_NAME:$PROCESSOR_DOCKER_TAG"

docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$WEBHOOK_DOCKER_REPO_NAME:$WEBHOOK_DOCKER_TAG"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROCESSOR_DOCKER_REPO_NAME:$PROCESSOR_DOCKER_TAG"

# Configure sam
cat <<EOS > "samconfig-$ENVIRONMENT.toml"
version = 0.1

[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "$APP_NAME-$ENVIRONMENT"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
  'Environment=$ENVIRONMENT',
  'AppName=$APP_NAME',
  'LambdaMemorySize=$LAMBDA_MEMORY_SIZE',
  'WebhookDockerTag=$WEBHOOK_DOCKER_TAG',
  'ProcessorDockerTag=$PROCESSOR_DOCKER_TAG',
  'RequestKeepSec=$REQUEST_KEEP_SEC',
  'LineChannelSecret=$LINE_CHANNEL_SECRET',
  'LineChannelAccessToken=$LINE_CHANNEL_ACCESS_TOKEN',
  'OpenaiOrganization=$OPENAI_ORGANIZATION',
  'OpenaiApiKey=$OPENAI_API_KEY',
  'OpenaiModelName=$OPENAI_MODEL_NAME',
  'OpenaiModelMaxTokens=$OPENAI_MODEL_MAX_TOKENS',
  'OpenaiChatGptSystemMessage=$OPENAI_CHAT_GPT_SYSTEM_MESSAGE',
  'OpenaiRequestTimeout=$OPENAI_REQUEST_TIMEOUT',
  'OpenaiRequestTimeoutErrorMessage=$OPENAI_REQUEST_TIMEOUT_ERROR_MESSAGE',
  'QuickReply=$QUICK_REPLY'
]
image_repositories = ["LineBotWebhook=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$WEBHOOK_DOCKER_REPO_NAME", "LineBotProcessor=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROCESSOR_DOCKER_REPO_NAME"]
EOS

# Deploy by sam
export SAM_CLI_TELEMETRY=0
echo "sam deploy --guided --config-file samconfig-$ENVIRONMENT.toml --template-file template.yaml --region ${AWS_REGION} --profile $AWS_PROFILE"
sam deploy --guided --config-file "samconfig-$ENVIRONMENT.toml" --template-file template.yaml --region "${AWS_REGION}" --profile "$AWS_PROFILE"
