import os
import json
import datetime
import time
from common.logger_factory import LoggerFactory
from models.model_base import SortKeyComparison
from models.talk_room_history import TalkRoomHistory
from models.chat_gpt_request_history import ChatGptRequestHistory
from services.line import Line
from services.chatgpt import ChatGpt

# ログ出力設定
LOGGER_LEVEL = os.environ.get("LOGGER_LEVEL", "INFO")
logger = LoggerFactory.get_logger(__name__, log_level=LOGGER_LEVEL)

# タイムアウト秒数/エラーメッセージ設定
OPENAI_REQUEST_TIMEOUT = float(os.environ.get("OPENAI_REQUEST_TIMEOUT", 10))
OPENAI_REQUEST_TIMEOUT_ERROR_MESSAGE = (
    os.environ.get(
        "OPENAI_REQUEST_TIMEOUT_ERROR_MESSAGE", "The OpenAI API request has timed out."
    )
    .strip('"')
    .replace("\\n", "\n")
)


def is_message_event(event_body) -> bool:
    if event_body.get("event_type") == "text_message":
        return True
    elif event_body.get("event_type") == "image_message":
        return True
    elif event_body.get("event_type") == "video_message":
        return True
    elif event_body.get("event_type") == "audio_message":
        return True
    elif event_body.get("event_type") == "location_message":
        return True
    elif event_body.get("event_type") == "sticker_message":
        return True
    elif event_body.get("event_type") == "file_message":
        return True
    return False


def get_quick_reply():
    quick_reply_str = os.environ.get(
        "QUICK_REPLY",
        None,
    )
    try:
        if quick_reply_str:
            return json.loads(quick_reply_str)
    except Exception:
        logger.error("QUICK_REPLY is an invalid", exc_info=True)
    return None


def process_text_message_event(
    line_event, system_message: str = "", local: bool = False
) -> ChatGptRequestHistory | None:
    """LINEイベント(テキストメッセージ)の処理。
       テキストメッセージをChatGPTで処理し、処理結果を返す。

    Args:
        line_event: LINEイベント(テキストメッセージ)
         system_message: 空文字以外の場合に ChatGPT の振る舞いの定義に使われるメッセージ(テスト用)
         local: True の場合に DynamoDB Local を使用する(テスト用)

    Returns:
        ChatGptRequestHistory: ChatGPTへのリクエスト履歴オプジェクト(処理結果含む)
    """

    # トークルームの投稿を DynamoDB に保存
    talk_room_history = TalkRoomHistory.from_line_event(line_event, local=local)
    talk_room_history.save()
    text_message = talk_room_history.textMessage

    logger.info(talk_room_history.serialize())

    past_time = datetime.datetime.now() - datetime.timedelta(
        seconds=int(os.environ.get("REQUEST_KEEP_SEC", 604800))  # type: ignore
    )

    # ChatGPTへのリクエスト履歴を取得
    past_chatgpt_request_histories = ChatGptRequestHistory.find(
        ChatGptRequestHistory.get_query(
            talk_room_history.talkRoomId,
            SortKeyComparison.GE,
            sort_key1=past_time.isoformat(),
            limit=1,
            reverse=True,
        ),
        db_client=talk_room_history.get_db_client(),
    )
    past_request = []
    if len(past_chatgpt_request_histories) > 0:
        past_chatgpt_request_history = past_chatgpt_request_histories[0]
        past_request = json.loads(past_chatgpt_request_history.request)

    # 送信用メッセージ一覧に今回のメッセージと過去のリクエスト中のメッセージを含む ChatGpt オブジェクトを生成
    chatgpt = ChatGpt(
        system_message=system_message,
        text_message=text_message,
        past_request=past_request,
    )

    chatgpt_request_histories = ChatGptRequestHistory.find(
        ChatGptRequestHistory.get_gs2_query(
            ChatGptRequestHistory.hash_string(
                json.dumps(chatgpt.get_request(), ensure_ascii=False)
            ),
            limit=1,
            reverse=True,
        ),
        db_client=talk_room_history.get_db_client(),
    )
    if len(chatgpt_request_histories) > 0:
        chatgpt_request_history: ChatGptRequestHistory = chatgpt_request_histories[0]
        if chatgpt_request_history.createdAt > past_time.isoformat():
            # past_time から現時点までに同じ内容のリクエストを送信していた場合は、そのリクエスト履歴を返却
            return chatgpt_request_history

    try:
        if chatgpt.send(timeout=OPENAI_REQUEST_TIMEOUT):  # OpenAIのサーバにメッセージを送信
            # OpenAIのサーバに送信したリクエストと、受信したレスポンスを DynamoDB に保存
            chatgpt_request_history = ChatGptRequestHistory.create_instance(
                talk_room_history.talkRoomId,
                talk_room_history.userId,
                chatgpt.get_request(),  # OpenAIのサーバに送信したリクエスト
                chatgpt.get_response(),  # OpenAIのサーバから受信したレスポンス
                db_client=talk_room_history.get_db_client(),
            )
            chatgpt_request_history.save()

            logger.info(chatgpt_request_history.serialize())

            return chatgpt_request_history
    except Exception:
        logger.error("Request timed out", exc_info=True)
        # タイムアウトした場合は、タイムアウトエラーメッセージを返す
        chatgpt_request_history = ChatGptRequestHistory.create_instance(
            talk_room_history.talkRoomId,
            talk_room_history.userId,
            chatgpt.get_request(),  # OpenAIのサーバに送信したリクエスト
            error_message=OPENAI_REQUEST_TIMEOUT_ERROR_MESSAGE,
            db_client=talk_room_history.get_db_client(),
        )
        chatgpt_request_history.save()

        logger.info(chatgpt_request_history.serialize())

        return chatgpt_request_history
    return None


def process_sqs_event(event):
    if not event.get("Records") or type(event["Records"]) is not list:
        return
    for record in event["Records"]:
        if record.get("eventSource") == "aws:sqs":
            body = json.loads(record["body"])
            if is_message_event(body):
                if body.get("event_type") == "text_message":
                    model = process_text_message_event(body.get("line_event"))
                    if model:
                        Line.reply_text_message(
                            body.get("line_event"),
                            model.get_response_message_content(),
                            quick_reply=get_quick_reply(),
                        )
                else:
                    if body.get("event_type") == "image_message":
                        pass
                    elif body.get("event_type") == "video_message":
                        pass
                    elif body.get("event_type") == "audio_message":
                        pass
                    elif body.get("event_type") == "location_message":
                        pass
                    elif body.get("event_type") == "sticker_message":
                        pass
                    elif body.get("event_type") == "file_message":
                        pass
                    # テキスト以外のメッセージには、5秒待ってから固定のLINEスタンプを返す
                    # TODO: 投稿内容に応じた返信の実装、または、複数のLINEスタンプからランダムに選択
                    time.sleep(5)  # 5秒待つ
                    Line.reply_sticker_message(
                        body.get("line_event"),
                        package_id="11538",
                        sticker_id="51626499",
                    )
            else:
                # TODO: イベントごとに処理を記述
                if body.get("event_type") == "follow":
                    pass
                elif body.get("event_type") == "unfollow":
                    pass
                elif body.get("event_type") == "join":
                    pass
                elif body.get("event_type") == "leave":
                    pass
                elif body.get("event_type") == "member_joined":
                    pass
                elif body.get("event_type") == "member_left":
                    pass


def lambda_handler(event, context):
    logger.info(event)
    logger.info(json.dumps(event))
    try:
        process_sqs_event(event)
    except Exception:
        logger.error("Failed to process an event", exc_info=True)
