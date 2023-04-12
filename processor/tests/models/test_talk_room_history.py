import datetime
from unittest import TestCase
from models.db_client import DbClient
from models.model_base import SortKeyComparison
from models.talk_room_history import TalkRoomHistory


class TalkRoomHistoryTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        # Connect to DynamoDB local
        # cf. https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html
        cls.db_client = DbClient.get_client(local=True)

        # set time
        cls.past_time = datetime.datetime(
            2022, 12, 31, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        cls.current_time = datetime.datetime(
            2023, 1, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
        )

        # set table_name
        cls.table_name = "TalkRoomHistoryTable"

        cls.test_data = [
            {
                "talkRoomId": "R0123456789abcdef0123456789abcdef",
                "userId": "U0123456789abcdef0123456789abcdef",
                "textMessage": "This is a talk room history 1.",
                "createdAt": cls.past_time.isoformat(),
            },
            {
                "talkRoomId": "R0123456789abcdef0123456789abcdef",
                "userId": "U123456789abcdef0123456789abcdef0",
                "textMessage": "This is a talk room history 2.",
                "createdAt": cls.current_time.isoformat(),
            },
        ]
        TalkRoomHistory.create_table(db_client=cls.db_client, local=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db_client.delete_table(TableName=cls.table_name)
        cls.db_client.close()

    def test_save_find_delete_001(self):

        talk_room_history1 = TalkRoomHistory(
            self.test_data[0],
            self.db_client,
        )
        talk_room_history1.save()

        talk_room_history2 = TalkRoomHistory(
            self.test_data[1],
            self.db_client,
        )
        talk_room_history2.save()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(self.test_data[0]["talkRoomId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 2)
        self.assertDictEqual(talk_room_history1._data, records[0]._data)
        self.assertDictEqual(talk_room_history2._data, records[1]._data)

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(
                self.test_data[0]["talkRoomId"], limit=2, reverse=True
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 2)
        self.assertDictEqual(talk_room_history1._data, records[1]._data)
        self.assertDictEqual(talk_room_history2._data, records[0]._data)

        talk_room_history1.delete()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(
                self.test_data[1]["talkRoomId"],
                sort_op=SortKeyComparison.EQ,
                sort_key1=self.test_data[1]["createdAt"],
                limit=1,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)

        talk_room_history2.delete()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(
                self.test_data[1]["talkRoomId"],
                sort_op=SortKeyComparison.EQ,
                sort_key1=self.test_data[1]["createdAt"],
                limit=1,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 0)

    def test_save_find_delete_002(self):

        talk_room_history1 = TalkRoomHistory(
            self.test_data[0],
            self.db_client,
        )
        talk_room_history1.save()

        talk_room_history2 = TalkRoomHistory(
            self.test_data[1],
            self.db_client,
        )
        talk_room_history2.save()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_gs1_query(self.test_data[0]["userId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history1._data, records[0]._data)

        talk_room_history1.delete()
        talk_room_history2.delete()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(self.test_data[0]["talkRoomId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 0)

    def test_save_find_delete_003(self):

        talk_room_history1 = TalkRoomHistory(
            self.test_data[0],
            self.db_client,
        )
        talk_room_history1.save()

        talk_room_history2 = TalkRoomHistory(
            self.test_data[1],
            self.db_client,
        )
        talk_room_history2.save()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(
                self.test_data[0]["talkRoomId"],
                sort_op=SortKeyComparison.GE,
                sort_key1=self.current_time.isoformat(),
                limit=2,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history2._data, records[0]._data)

        talk_room_history1.delete()
        talk_room_history2.delete()

        records = TalkRoomHistory.find(
            TalkRoomHistory.get_query(self.test_data[0]["talkRoomId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 0)

    def test_from_line_event_001(self):
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
                "text": "Good Morning!! (love)",
                "emojis": [
                    {
                        "index": 29,
                        "length": 6,
                        "productId": "5ac1bfd5040ab15980c9b435",
                        "emojiId": "001",
                    }
                ],
            },
        }
        true_result = TalkRoomHistory(
            {
                "talkRoomId": "Ca56f94637c0000000000000000000000",
                "userId": "U4af49806290000000000000000000000",
                "textMessage": "Good Morning!! (love)",
                "createdAt": self.current_time.isoformat(),
            },
            db_client=self.db_client,
        )
        result = TalkRoomHistory.from_line_event(test_data, local=True)
        result.createdAt = self.current_time.isoformat()
        self.assertEqual(result.serialize(), true_result.serialize())
