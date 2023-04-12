import datetime
import json
from unittest import TestCase
from models.db_client import DbClient
from models.model_base import SortKeyComparison
from models.chat_gpt_request_history import ChatGptRequestHistory


class ChatGptRequestHistoryTestCase(TestCase):
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
        cls.table_name = "ChatGptRequestHistoryTable"

        cls.test_data = [
            {
                "talkRoomId": "R0123456789abcdef0123456789abcdef",
                "userId": "U0123456789abcdef0123456789abcdef",
                "requestId": ChatGptRequestHistory.hash_string(
                    json.dumps(
                        [
                            {"role": "system", "content": "You are the ChatGPT."},
                            {"role": "user", "content": "Hi, ChatGPT!"},
                        ],
                        ensure_ascii=False,
                    )
                ),
                "request": json.dumps(
                    [
                        {"role": "system", "content": "You are the ChatGPT."},
                        {"role": "user", "content": "Hi, ChatGPT!"},
                    ],
                    ensure_ascii=False,
                ),
                "response": json.dumps(
                    {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "index": 0,
                                "message": {
                                    "content": "Hello! How can I assist you today?",
                                    "role": "assistant",
                                },
                            }
                        ],
                        "created": 1679540861,
                        "id": "chatcmpl-6x5afj23U2zRuQvKPau349AfkVMGy",
                        "model": "gpt-3.5-turbo-0301",
                        "object": "chat.completion",
                        "usage": {
                            "completion_tokens": 10,
                            "prompt_tokens": 25,
                            "total_tokens": 35,
                        },
                    },
                    ensure_ascii=False,
                ),
                "createdAt": cls.past_time.isoformat(),
            },
            {
                "talkRoomId": "R0123456789abcdef0123456789abcdef",
                "userId": "U123456789abcdef0123456789abcdef0",
                "requestId": ChatGptRequestHistory.hash_string(
                    json.dumps(
                        [
                            {
                                "role": "system",
                                "content": "You are a teacher of mathematics.",
                            },
                            {
                                "role": "user",
                                "content": "Please tell me the answer of the following formula.\nexp(log(2 * PI * i))",
                            },
                        ],
                        ensure_ascii=False,
                    )
                ),
                "request": json.dumps(
                    [
                        {
                            "role": "system",
                            "content": "You are a teacher of mathematics.",
                        },
                        {
                            "role": "user",
                            "content": "Please tell me the answer of the following formula.\nexp(log(2 * PI * i))",
                        },
                    ],
                    ensure_ascii=False,
                ),
                "response": json.dumps(
                    {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "index": 0,
                                "message": {
                                    "content": "\n\nThe answer to the formula exp(log(2 * PI * i)) is simply 2 * PI * i. \n\nThis is because the exponential function (exp) is the inverse of the natural logarithm function (log), and they cancel each other out. So, when you take the exponential of the logarithm of a number, you get back the original number. \n\nIn this case, the logarithm of 2 * PI * i is simply log(2 * PI * i) = log(2) + log(PI) + log(i), and when you take the exponential of this, you get:\n\nexp(log(2) + log(PI) + log(i)) = exp(log(2)) * exp(log(PI)) * exp(log(i))\n\n= 2 * PI * i\n\nTherefore, the answer to the formula is 2 * PI * i.",
                                    "role": "assistant",
                                },
                            }
                        ],
                        "created": 1679541777,
                        "id": "chatcmpl-6x5pRSkaNoO7vOtLHrDfFUT4c9Ccb",
                        "model": "gpt-3.5-turbo-0301",
                        "object": "chat.completion",
                        "usage": {
                            "completion_tokens": 180,
                            "prompt_tokens": 38,
                            "total_tokens": 218,
                        },
                    },
                    ensure_ascii=False,
                ),
                "createdAt": cls.current_time.isoformat(),
            },
        ]
        ChatGptRequestHistory.create_table(db_client=cls.db_client, local=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db_client.delete_table(TableName=cls.table_name)
        cls.db_client.close()

    def test_save_find_delete_001(self):

        talk_room_history1 = ChatGptRequestHistory(
            self.test_data[0],
            self.db_client,
        )
        talk_room_history1.save()

        talk_room_history2 = ChatGptRequestHistory(
            self.test_data[1],
            self.db_client,
        )
        talk_room_history2.save()

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(self.test_data[0]["talkRoomId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 2)
        self.assertDictEqual(talk_room_history1._data, records[0]._data)
        self.assertDictEqual(talk_room_history2._data, records[1]._data)

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(
                self.test_data[0]["talkRoomId"], limit=2, reverse=True
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 2)
        self.assertDictEqual(talk_room_history1._data, records[1]._data)
        self.assertDictEqual(talk_room_history2._data, records[0]._data)

        talk_room_history1.delete()

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(
                self.test_data[1]["talkRoomId"],
                sort_op=SortKeyComparison.EQ,
                sort_key1=self.test_data[1]["createdAt"],
                limit=1,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)

        talk_room_history2.delete()

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(
                self.test_data[1]["talkRoomId"],
                sort_op=SortKeyComparison.EQ,
                sort_key1=self.test_data[1]["createdAt"],
                limit=1,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 0)

    def test_save_find_delete_002(self):

        talk_room_history1 = ChatGptRequestHistory(
            self.test_data[0],
            self.db_client,
        )
        talk_room_history1.save()

        talk_room_history2 = ChatGptRequestHistory(
            self.test_data[1],
            self.db_client,
        )
        talk_room_history2.save()

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_gs1_query(self.test_data[0]["userId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history1._data, records[0]._data)

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_gs2_query(
                self.test_data[0]["requestId"], limit=2, reverse=True
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history1._data, records[0]._data)

        talk_room_history1.delete()
        talk_room_history2.delete()
        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(self.test_data[0]["talkRoomId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 0)

    def test_save_find_delete_003(self):

        talk_room_history1 = ChatGptRequestHistory(
            self.test_data[0],
            self.db_client,
        )
        talk_room_history1.save()

        talk_room_history2 = ChatGptRequestHistory(
            self.test_data[1],
            self.db_client,
        )
        talk_room_history2.save()

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(
                self.test_data[0]["talkRoomId"],
                sort_op=SortKeyComparison.GE,
                sort_key1=self.current_time.isoformat(),
                limit=2,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history2._data, records[0]._data)

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_gs1_query(
                self.test_data[0]["userId"],
                sort_op=SortKeyComparison.GE,
                sort_key1=self.past_time.isoformat(),
                limit=2,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history1._data, records[0]._data)

        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_gs2_query(
                self.test_data[1]["requestId"],
                sort_op=SortKeyComparison.GT,
                sort_key1=self.past_time.isoformat(),
                limit=2,
            ),
            self.db_client,
        )
        self.assertEqual(len(records), 1)
        self.assertDictEqual(talk_room_history2._data, records[0]._data)

        talk_room_history1.delete()
        talk_room_history2.delete()
        records = ChatGptRequestHistory.find(
            ChatGptRequestHistory.get_query(self.test_data[0]["talkRoomId"], limit=2),
            self.db_client,
        )
        self.assertEqual(len(records), 0)
