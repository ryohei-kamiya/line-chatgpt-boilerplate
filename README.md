# line-chatgpt-boilerplate

This is a boilerplate for the LINE app that uses ChatGPT's API.

## Requirements

- [AWS Account](https://aws.amazon.com/)
    - Account ID
- [LINE Messaging API](https://developers.line.biz/en/docs/line-things/getting-started/#create-messaging-api-channel)
    - Channel Secret
    - Access Token (long-lived)
- [OpenAI API](https://openai.com/blog/openai-api)
    - Organization ID
    - API Key
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [SAM CLI](https://aws.amazon.com/serverless/sam/)
- Docker
- bash

## How to Use

1. Rename .env-example to .env
2. Define the following environment variables in .env:
    1. AWS_ACCOUNT_ID
    2. AWS_REGION
    3. AWS_PROFILE
    4. ENVIRONMENT ( Arbitrary ASCII code string. ex. dev or prod )
    5. APP_NAME ( Arbitrary ASCII code string )
    6. [LINE_CHANNEL_SECRET](https://developers.line.biz/en/docs/line-things/getting-started/#create-messaging-api-channel)
    7. [LINE_CHANNEL_ACCESS_TOKEN](https://developers.line.biz/en/docs/messaging-api/channel-access-tokens/#long-lived-channel-access-tokens)
    8. [OPENAI_ORGANIZATION](https://platform.openai.com/docs/api-reference/requesting-organization)
    9. [OPENAI_API_KEY](https://platform.openai.com/docs/api-reference/authentication)
    10. [OPENAI_CHAT_GPT_SYSTEM_MESSAGE](https://platform.openai.com/docs/guides/chat/introduction)
3. Run `build.sh`
4. Run `deploy.sh`
    1. Answer the questions displayed on the screen (generally, there is no problem with answering Yes to all).
    2. Take note of the LineBotWebhookUrl value outputted at the end.
    3. [Set the LineBotWebhookUrl value](https://developers.line.biz/en/docs/messaging-api/building-bot/#set-up-bot-on-line-developers-console) on the LINE Developers Console.
5. Please refer to the [LINE Developers Documentation](https://developers.line.biz/en/docs/) and configure other settings accordingly.
