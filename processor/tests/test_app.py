import datetime
import warnings
from unittest import TestCase
from models.db_client import DbClient
from models.talk_room_history import TalkRoomHistory
from models.chat_gpt_request_history import ChatGptRequestHistory
import app


class AppTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        # Connect to DynamoDB local
        # cf. https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html
        cls.db_client = DbClient.get_client(local=True)

        # set time
        cls.current_time = datetime.datetime(
            2023, 1, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
        )

        TalkRoomHistory.create_table(db_client=cls.db_client, local=True)
        ChatGptRequestHistory.create_table(db_client=cls.db_client, local=True)

        warnings.simplefilter("ignore", ResourceWarning)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db_client.delete_table(TableName="TalkRoomHistoryTable")
        cls.db_client.delete_table(TableName="ChatGptRequestHistoryTable")
        cls.db_client.close()

    def test_process_text_message_event_001(self):
        test_data = {
            "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
            "type": "message",
            "mode": "active",
            "timestamp": 1462629479859,
            "source": {
                "type": "group",
                "groupId": "Ca56f94637c0000000000000000000000",
                "userId": "U4af49806290000000000000000000000",
            },
            "webhookEventId": "01FZ74A0TDDPYRVKNK77XKC3ZR",
            "deliveryContext": {"isRedelivery": False},
            "message": {
                "id": "444573844083572737",
                "type": "text",
                "text": "What is your favorite sport?",
            },
        }
        result = app.process_text_message_event(
            test_data, system_message="You are a baseball player.", local=True
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.talkRoomId, "Ca56f94637c0000000000000000000000")  # type: ignore
        self.assertEqual(result.userId, "U4af49806290000000000000000000000")  # type: ignore
