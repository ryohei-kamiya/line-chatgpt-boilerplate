import os
import openai
import tiktoken
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

openai.organization = os.environ.get("OPENAI_ORGANIZATION", "").strip("\"'")
openai.api_key = os.environ.get("OPENAI_API_KEY", "").strip("\"'")


class ChatGptRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    @classmethod
    def value_of(cls, target_value):
        for e in ChatGptRole:
            if e.value == target_value:
                return e
        raise ValueError("{} is not a valid role.".format(target_value))


class ChatGpt:
    def __init__(
        self,
        model_name: str = "",
        max_tokens: int = 0,
        system_message: str = "",
        text_message: str = "",
        past_request: list = [],
    ) -> None:
        if not model_name:
            model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo").strip(
                "\"'"
            )
        if not max_tokens:
            max_tokens = int(os.environ.get("OPENAI_MODEL_MAX_TOKENS", 4096))  # type: ignore
        if not system_message:
            system_message = os.environ.get(
                "OPENAPI_CHAT_GPT_SYSTEM_MESSAGE", "This is a default system."
            ).strip("\"'")
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.response = None
        self.tokens = self.count_tokens(system_message)
        self.request = [{"role": ChatGptRole.SYSTEM.value, "content": system_message}]

        if text_message:
            remaining_available_tokens = self.remaining_available_tokens(text_message)
            if remaining_available_tokens < 0:
                # トークン数の制限を超える分のテキストは切り捨てる
                text_message = text_message[:remaining_available_tokens]
            # text_messageを送信用メッセージリストに追加
            while not self.add_message(ChatGptRole.USER, text_message):
                # トークン数の制限を超える場合は追加されない
                # その場合はテキストの末尾を切り捨てて追加できるまで繰り返す
                text_message = text_message[:-1]

        if past_request and type(past_request) is list:
            for message in reversed(past_request):
                if type(message) is dict:
                    # 過去の受け答えを、新しい順に送信用メッセージリストに追加
                    if not self.add_message(
                        ChatGptRole.value_of(message.get("role")),
                        message.get("content", ""),
                        reverse=True,
                    ):
                        # 追加できなくなった時点で終了(トークン制限を超える古いメッセージは無視)
                        break

    def count_tokens(self, content: str | None) -> int:
        if not content:
            return 0
        enc = tiktoken.encoding_for_model(self.model_name)
        return len(enc.encode(content))

    def remaining_available_tokens(self, content: str) -> int:
        _tokens = self.count_tokens(content)
        return self.max_tokens - (self.tokens + _tokens)

    def add_message(
        self, role: ChatGptRole, content: str, reverse: bool = False
    ) -> bool:
        if role == ChatGptRole.SYSTEM:
            return False
        _tokens = self.count_tokens(content)
        if self.tokens + _tokens > self.max_tokens:
            return False
        if reverse:
            self.request.insert(1, {"role": role.value, "content": content})
        else:
            self.request.append({"role": role.value, "content": content})
        self.tokens += _tokens
        return True

    def send(self, timeout: float | None = None) -> bool:
        if len(self.request) < 2:
            return False
        if self.request[1]["role"] == ChatGptRole.ASSISTANT.value:
            del self.request[1]
            if len(self.request) < 2:
                return False
        if timeout is not None:
            tpe = ThreadPoolExecutor(max_workers=1)
            try:
                future = tpe.submit(
                    openai.ChatCompletion.create,
                    model=self.model_name,
                    messages=self.request,
                    timeout=timeout,
                )
                self.response = future.result(timeout=timeout)
            except FutureTimeoutError:
                tpe.shutdown(wait=False, cancel_futures=True)
                raise
        else:
            self.response = openai.ChatCompletion.create(
                model=self.model_name, messages=self.request
            )
        return True

    def get_request(self):
        return self.request

    def get_response(self) -> dict:
        return self.response  # type: ignore

    def get_response_message_content(self, n: int = 0):
        response = self.get_response()
        if not response:
            return None
        if response.get("error_message"):
            return response["error_message"]
        if not response.get("choices"):
            return None
        if len(response["choices"]) <= n:
            return None
        if not response["choices"][n].get("message"):
            return None
        if not response["choices"][n]["message"].get("content"):
            return None
        return response["choices"][n]["message"]["content"]
