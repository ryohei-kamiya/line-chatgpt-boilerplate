import os
import sys
from linebot import LineBotApi
from linebot.models import TextSendMessage, StickerSendMessage
from common.logger_factory import LoggerFactory

# ログ出力設定
LOGGER_LEVEL = os.environ.get("LOGGER_LEVEL", "INFO")
logger = LoggerFactory.get_logger(__name__, log_level=LOGGER_LEVEL)

channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip("\"'")
if channel_access_token is None:
    logger.error("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)


class Line:

    line_bot_api = LineBotApi(channel_access_token)

    @classmethod
    def reply_text_message(
        cls, line_event, text_message: str | None, quick_reply: list | None = None
    ):
        if text_message:
            if quick_reply and len(quick_reply) > 0 and type(quick_reply[0]) is dict:
                cls.line_bot_api.reply_message(
                    line_event.get("replyToken"),
                    TextSendMessage(text=text_message, quick_reply=quick_reply),
                )
            else:
                cls.line_bot_api.reply_message(
                    line_event.get("replyToken"), TextSendMessage(text=text_message)
                )

    @classmethod
    def reply_sticker_message(
        cls,
        line_event,
        package_id: str,
        sticker_id: str,
        quick_reply: list | None = None,
    ):
        if package_id and sticker_id:
            if quick_reply and len(quick_reply) > 0 and type(quick_reply[0]) is dict:
                cls.line_bot_api.reply_message(
                    line_event.get("replyToken"),
                    StickerSendMessage(
                        package_id=package_id,
                        sticker_id=sticker_id,
                        quick_reply=quick_reply,
                    ),
                )
            else:
                cls.line_bot_api.reply_message(
                    line_event.get("replyToken"),
                    StickerSendMessage(
                        package_id=package_id,
                        sticker_id=sticker_id,
                    ),
                )
