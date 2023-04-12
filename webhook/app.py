import os
import sys
import json
import logging
import boto3
import uuid
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    FollowEvent,
    UnfollowEvent,
    MessageEvent,
    PostbackEvent,
    JoinEvent,
    LeaveEvent,
    MemberJoinedEvent,
    MemberLeftEvent,
    TextMessage,
    TextSendMessage,
    ImageMessage,
    VideoMessage,
    AudioMessage,
    LocationMessage,
    StickerMessage,
    FileMessage,
)
from linebot.exceptions import LineBotApiError, InvalidSignatureError
from common import utils

# ログ出力設定
LOGGER_LEVEL = os.environ.get("LOGGER_LEVEL")
logger = logging.getLogger()
if LOGGER_LEVEL == "DEBUG":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
if channel_secret is None:
    logger.error("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    logger.error("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

queue_url = os.environ.get("SQS_QUEUE_URL", "")

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
sqs_client = boto3.client("sqs")


def get_sigunature(key_search_dict):
    """
    署名発行に必要なx-line-signatureを大文字小文字区別せずに取得し、署名内容を返却する

    Parameters
    ----------
    key_search_dict : dict
        Webhookへのリクエストのheaders

    Returns
    -------
    signature : str
        LINE Botの署名
    """
    for key in key_search_dict.keys():
        if key.lower() == "x-line-signature":
            signature = key_search_dict[key]
            return signature


def convert_user_id(event):
    """
    LINE UserIdのマスク処理

    Parameters
    ----------
    event : dict
        Webhookへのリクエスト内容。

    Returns
    -------
    log_event : dict
        UserIdマスク後のリクエスト内容。
    """
    log_body = json.loads(event["body"])
    update_body = []
    for linebot_event in log_body["events"]:
        linebot_event["source"]["userId"] = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        update_body.append(linebot_event)
    del log_body["events"]
    log_body["events"] = update_body
    log_event = event
    log_event["body"] = json.dumps(log_body, ensure_ascii=False)

    return log_event


def get_fifo_message_group_id(line_event):
    _line_event = line_event.as_json_dict()
    if _line_event.get("source"):
        user_id = _line_event["source"].get("userId", "")
        group_id = _line_event["source"].get("groupId", "")
        talk_room_id = _line_event["source"].get("roomId", "")
        if not talk_room_id:
            if group_id:
                talk_room_id = group_id
            elif user_id:
                talk_room_id = user_id
        return talk_room_id
    return "line-bot-using-chatgpt"


def get_fifo_message_deduplication_id():
    return str(uuid.uuid4())


@handler.add(PostbackEvent)
def postback(line_event):
    """
    Webhookに送信されたLINEポストバックイベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINEポストバックイベント内容。

    """

    param_list = line_event.postback.data.split("&")
    action = None
    action_type = None
    for param in param_list:
        if param.split("=")[0] == "action":
            action = param.split("=")[1]
        elif param.split("=")[0] == "action_type":
            action_type = param.split("=")[1]
        elif param.split("=")[0] == "lang":
            # TODO: setup the language
            # language = param.split("=")[1]
            pass

    if action == "quick_reply":
        if action_type == "yes":
            line_bot_api.reply_message(
                line_event.reply_token, TextSendMessage(text="YES is selected.")
            )
        else:
            line_bot_api.reply_message(
                line_event.reply_token, TextSendMessage(text="NO is selected.")
            )
    else:
        logger.error("[ERROR]Detect an undefined action!")


@handler.add(MessageEvent, message=TextMessage)
def text_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(テキスト)について処理を実施する

    Parameters
    ----------
    line_event : dict
        LINEメッセージイベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "text_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MessageEvent, message=ImageMessage)
def image_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(画像)について処理を実施する
    Parameters
    ----------
    line_event: dict
        LINEメッセージイベント内容。
    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "image_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MessageEvent, message=VideoMessage)
def video_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(動画)について処理を実施する
    Parameters
    ----------
    line_event: dict
        LINEメッセージイベント内容。
    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "video_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MessageEvent, message=AudioMessage)
def audio_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(音声)について処理を実施する
    Parameters
    ----------
    line_event: dict
        LINEメッセージイベント内容。
    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "audio_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MessageEvent, message=LocationMessage)
def location_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(位置情報)について処理を実施する
    Parameters
    ----------
    line_event: dict
        LINEメッセージイベント内容。
    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "location_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MessageEvent, message=StickerMessage)
def sticker_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(スタンプ)について処理を実施する
    Parameters
    ----------
    line_event: dict
        LINEメッセージイベント内容。
    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "sticker_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MessageEvent, message=FileMessage)
def file_message(line_event):
    """
    Webhookに送信されたLINEメッセージイベント(ファイル)について処理を実施する
    Parameters
    ----------
    line_event: dict
        LINEメッセージイベント内容。
    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "file_message",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(FollowEvent)
def follow(line_event):
    """
    Webhookに送信されたLINEフォローイベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINEフォローイベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "follow",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(UnfollowEvent)
def unfollow(line_event):
    """
    Webhookに送信されたLINEフォロー解除イベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINEフォロー解除イベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "unfollow",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(JoinEvent)
def join(line_event):
    """
    Webhookに送信されたLINE参加イベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINE参加イベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "join",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(LeaveEvent)
def leave(line_event):
    """
    Webhookに送信されたLINE退出イベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINE退出イベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "leave",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MemberJoinedEvent)
def member_joined(line_event):
    """
    Webhookに送信されたLINEメンバー参加イベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINEメンバー参加イベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "member_joined",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


@handler.add(MemberLeftEvent)
def member_left(line_event):
    """
    Webhookに送信されたLINEメンバー退出イベントについて処理を実施する

    Parameters
    ----------
    line_event: dict
        LINEメンバー退出イベント内容。

    """
    # SQSにメッセージを通知
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "event_type": "member_left",
                "line_event": line_event.as_json_dict(),
            },
            ensure_ascii=False,
        ),
        MessageGroupId=get_fifo_message_group_id(line_event),
        MessageDeduplicationId=get_fifo_message_deduplication_id(),
    )


def lambda_handler(event, context):
    """
    Webhookに送信されたLINEトーク内容を返却する

    Parameters
    ----------
    event : dict
        Webhookへのリクエスト内容。
    context : dict
        コンテキスト内容。

    Returns
    -------
    Response : dict
        Webhookへのレスポンス内容。
    """
    log_event = event.copy()
    logger.info(convert_user_id(log_event))
    signature = get_sigunature(event["headers"])
    body = event["body"]
    error_json = utils.create_error_response("Error")
    error_json["isBase64Encoded"] = False

    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        logger.error(
            "Got exception from LINE Messaging API: %s\n" % e.message, exc_info=True
        )
        return error_json
    except InvalidSignatureError as e:
        logger.error(
            "Got exception from LINE Messaging API: %s\n" % e.message, exc_info=True
        )
        return error_json
    else:
        ok_json = utils.create_success_response(json.dumps("Success"))
        ok_json["isBase64Encoded"] = False
        return ok_json
