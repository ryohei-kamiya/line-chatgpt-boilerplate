import os
from unittest import TestCase
from services.chatgpt import ChatGpt, ChatGptRole
from concurrent.futures import TimeoutError as FutureTimeoutError


class ChatGptTestCase(TestCase):
    def test_init_001(self):
        chatgpt = ChatGpt(
            model_name="gpt-3.5-turbo",
            max_tokens=4096,
            system_message="You are the ChatGPT.",
        )
        request = chatgpt.get_request()
        self.assertDictEqual(
            request[0],
            {"role": ChatGptRole.SYSTEM.value, "content": "You are the ChatGPT."},
        )

        chatgpt = ChatGpt(
            model_name="gpt-3.5-turbo",
            max_tokens=4096,
            system_message="You are the ChatGPT.",
            text_message="Hi, ChatGPT!",
        )
        request = chatgpt.get_request()
        self.assertDictEqual(
            request[0],
            {"role": ChatGptRole.SYSTEM.value, "content": "You are the ChatGPT."},
        )
        self.assertDictEqual(
            request[1], {"role": ChatGptRole.USER.value, "content": "Hi, ChatGPT!"}
        )

        chatgpt = ChatGpt(
            model_name="gpt-3.5-turbo",
            max_tokens=4096,
            past_request=[
                {"role": ChatGptRole.SYSTEM.value, "content": "You are the ChatGPT."},
                {"role": ChatGptRole.USER.value, "content": "Hi, ChatGPT!"},
                {
                    "role": ChatGptRole.ASSISTANT.value,
                    "content": "Hello! How can I assist you today?",
                },
            ],
        )
        request = chatgpt.get_request()
        self.assertDictEqual(
            request[0],
            {
                "role": ChatGptRole.SYSTEM.value,
                "content": os.environ.get(
                    "OPENAPI_CHAT_GPT_SYSTEM_MESSAGE", "This is a default system."
                ).strip("\"'"),
            },
        )
        self.assertDictEqual(
            request[1], {"role": ChatGptRole.USER.value, "content": "Hi, ChatGPT!"}
        )
        self.assertDictEqual(
            request[2],
            {
                "role": ChatGptRole.ASSISTANT.value,
                "content": "Hello! How can I assist you today?",
            },
        )

        chatgpt = ChatGpt(
            model_name="gpt-3.5-turbo",
            max_tokens=4096,
            text_message="No thanks. This is a test.",
            past_request=[
                {"role": ChatGptRole.SYSTEM.value, "content": "You are the ChatGPT."},
                {"role": ChatGptRole.USER.value, "content": "Hi, ChatGPT!"},
                {
                    "role": ChatGptRole.ASSISTANT.value,
                    "content": "Hello! How can I assist you today?",
                },
            ],
        )
        request = chatgpt.get_request()
        self.assertDictEqual(
            request[0],
            {
                "role": ChatGptRole.SYSTEM.value,
                "content": os.environ.get(
                    "OPENAPI_CHAT_GPT_SYSTEM_MESSAGE", "This is a default system."
                ).strip("\"'"),
            },
        )
        self.assertDictEqual(
            request[1], {"role": ChatGptRole.USER.value, "content": "Hi, ChatGPT!"}
        )
        self.assertDictEqual(
            request[2],
            {
                "role": ChatGptRole.ASSISTANT.value,
                "content": "Hello! How can I assist you today?",
            },
        )
        self.assertDictEqual(
            request[3],
            {"role": ChatGptRole.USER.value, "content": "No thanks. This is a test."},
        )

    def test_send_001(self):
        chatgpt = ChatGpt(
            model_name="gpt-3.5-turbo",
            max_tokens=4096,
            system_message="You are the ChatGPT.",
            text_message="reactを使って入力フォームを作る場合のサンプルコードを提示してください。",
            past_request=[],
        )
        self.assertRaises(FutureTimeoutError, chatgpt.send, 0.0001)
