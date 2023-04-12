import os
import json
import datetime
import hashlib
from models.db_client import DbClient
from models.model_base import ModelBase, SortKeyComparison


class ChatGptRequestHistory(ModelBase):

    TABLE = os.getenv(
        "DYNAMO_CHAT_GPT_REQUEST_HISTORY_TABLE", "ChatGptRequestHistoryTable"
    )

    def __init__(
        self, data: dict, db_client: DbClient | None = None, local: bool = False
    ):
        super().__init__(db_client, local=local)
        self._schema = {
            "type": "object",
            "properties": {
                "talkRoomId": {
                    "type": "string",
                    "minLength": 33,
                    "maxLength": 33,
                    "pattern": r"^U[0-9a-f]{32}$|^C[0-9a-f]{32}$|^R[0-9a-f]{32}$",
                },
                "userId": {
                    "type": "string",
                    "minLength": 33,
                    "maxLength": 33,
                    "pattern": r"^U[0-9a-f]{32}$",
                },
                "requestId": {
                    "type": "string",  # JSON string
                    "minLength": 64,
                    "maxLength": 64,
                },
                "request": {
                    "type": "string",  # JSON string
                    "minLength": 0,
                    "maxLength": 100000,
                },
                "response": {
                    "type": "string",
                    "minLength": 0,
                    "maxLength": 100000,
                },
                "createdAt": {
                    "type": "string",
                    "pattern": r"^(?:[\+-]?\d{4}(?!\d{2}\b))(?:(-?)(?:(?:0[1-9]|1[0-2])(?:\1(?:[12]\d|0[1-9]|3[01]))?|W(?:[0-4]\d|5[0-2])(?:-?[1-7])?|(?:00[1-9]|0[1-9]\d|[12]\d{2}|3(?:[0-5]\d|6[1-6])))(?:[T\s](?:(?:(?:[01]\d|2[0-3])(?:(:?)[0-5]\d)?|24\:?00)(?:[\.,]\d+(?!:))?)?(?:\2[0-5]\d(?:[\.,]\d+)?)?(?:[zZ]|(?:[\+-])(?:[01]\d|2[0-3]):?(?:[0-5]\d)?)?)?)?$",
                },
            },
        }
        self._data = data

    @classmethod
    def hash_string(cls, string):
        """与えられた文字列をハッシュ化する"""
        encoded_string = string.encode("utf-8")
        hash_object = hashlib.sha256(encoded_string)
        hash_string = hash_object.hexdigest()
        return hash_string

    @classmethod
    def create_instance(
        cls,
        talk_room_id: str,
        user_id: str,
        request: list,
        response: dict | None = None,
        error_message: str | None = None,
        db_client: DbClient | None = None,
    ) -> "ChatGptRequestHistory":
        request_str = json.dumps(request, ensure_ascii=False)
        request_id = cls.hash_string(request_str)
        if error_message or not response:
            if not error_message:
                error_message = "empty response"
            return ChatGptRequestHistory(
                {
                    "talkRoomId": talk_room_id,
                    "userId": user_id,
                    "requestId": request_id,
                    "request": request_str,
                    "response": {"error_message": error_message},
                    "createdAt": datetime.datetime.now().isoformat(),
                },
                db_client=db_client,
            )
        else:
            return ChatGptRequestHistory(
                {
                    "talkRoomId": talk_room_id,
                    "userId": user_id,
                    "requestId": request_id,
                    "request": request_str,
                    "response": json.dumps(response, ensure_ascii=False),
                    "createdAt": datetime.datetime.now().isoformat(),
                },
                db_client=db_client,
            )

    @classmethod
    def create_table(cls, db_client: DbClient | None = None, local: bool = False):
        if not db_client:
            db_client = DbClient.get_client(local=local)
        db_client.create_table(
            TableName=cls.TABLE,
            AttributeDefinitions=[
                {"AttributeName": "talkRoomId", "AttributeType": "S"},
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "requestId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "talkRoomId", "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": cls.TABLE + "GSI1",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {
                        "ProjectionType": "INCLUDE",
                        "NonKeyAttributes": [
                            "talkRoomId",
                            "requestId",
                            "request",
                            "response",
                        ],
                    },
                },
                {
                    "IndexName": cls.TABLE + "GSI2",
                    "KeySchema": [
                        {"AttributeName": "requestId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {
                        "ProjectionType": "INCLUDE",
                        "NonKeyAttributes": [
                            "talkRoomId",
                            "userId",
                            "requestId",
                            "request",
                            "response",
                        ],
                    },
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    @classmethod
    def get_table(cls) -> str:
        return cls.TABLE

    @classmethod
    def get_query(
        cls,
        partition_key: str,
        sort_op: SortKeyComparison | None = None,
        sort_key1: str | None = None,
        sort_key2: str | None = None,
        limit: int = 1,
        reverse: bool = False,
    ) -> dict:
        if sort_op and sort_key1:
            if sort_op == SortKeyComparison.EQ:
                return {
                    "TableName": cls.get_table(),
                    "KeyConditionExpression": "talkRoomId = :talkRoomId AND createdAt = :createdAt",
                    "ExpressionAttributeValues": {
                        ":talkRoomId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                }
            elif sort_op == SortKeyComparison.LT:
                return {
                    "TableName": cls.get_table(),
                    "KeyConditionExpression": "talkRoomId = :talkRoomId AND createdAt < :createdAt",
                    "ExpressionAttributeValues": {
                        ":talkRoomId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.LE:
                return {
                    "TableName": cls.get_table(),
                    "KeyConditionExpression": "talkRoomId = :talkRoomId AND createdAt <= :createdAt",
                    "ExpressionAttributeValues": {
                        ":talkRoomId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.GT:
                return {
                    "TableName": cls.get_table(),
                    "KeyConditionExpression": "talkRoomId = :talkRoomId AND createdAt > :createdAt",
                    "ExpressionAttributeValues": {
                        ":talkRoomId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.GE:
                return {
                    "TableName": cls.get_table(),
                    "KeyConditionExpression": "talkRoomId = :talkRoomId AND createdAt >= :createdAt",
                    "ExpressionAttributeValues": {
                        ":talkRoomId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.BETWEEN:
                if sort_key2:
                    return {
                        "TableName": cls.get_table(),
                        "KeyConditionExpression": "talkRoomId = :talkRoomId AND createdAt BETWEEN :createdAt1 AND :createdAt2",
                        "ExpressionAttributeValues": {
                            ":talkRoomId": {"S": partition_key},
                            ":createdAt1": {"S": sort_key1},
                            ":createdAt2": {"S": sort_key2},
                        },
                        "ScanIndexForward": not reverse,
                        "Limit": limit,
                    }
                else:
                    return {}
            elif sort_op == SortKeyComparison.BEGINS_WITH:
                return {
                    "TableName": cls.get_table(),
                    "KeyConditionExpression": "talkRoomId = :talkRoomId AND begins_with ( createdAt, :createdAt )",
                    "ExpressionAttributeValues": {
                        ":talkRoomId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
        return {
            "TableName": cls.get_table(),
            "KeyConditionExpression": "talkRoomId = :talkRoomId",
            "ExpressionAttributeValues": {":talkRoomId": {"S": partition_key}},
            "ScanIndexForward": not reverse,
            "Limit": limit,
        }

    @classmethod
    def get_gs1_query(
        cls,
        partition_key: str,
        sort_op: SortKeyComparison | None = None,
        sort_key1: str | None = None,
        sort_key2: str | None = None,
        limit: int = 1,
        reverse: bool = False,
    ) -> dict:
        if sort_op and sort_key1:
            if sort_op == SortKeyComparison.EQ:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI1",
                    "KeyConditionExpression": "userId = :userId AND createdAt = :createdAt",
                    "ExpressionAttributeValues": {
                        ":userId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                }
            elif sort_op == SortKeyComparison.LT:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI1",
                    "KeyConditionExpression": "userId = :userId AND createdAt < :createdAt",
                    "ExpressionAttributeValues": {
                        ":userId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.LE:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI1",
                    "KeyConditionExpression": "userId = :userId AND createdAt <= :createdAt",
                    "ExpressionAttributeValues": {
                        ":userId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.GT:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI1",
                    "KeyConditionExpression": "userId = :userId AND createdAt > :createdAt",
                    "ExpressionAttributeValues": {
                        ":userId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.GE:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI1",
                    "KeyConditionExpression": "userId = :userId AND createdAt >= :createdAt",
                    "ExpressionAttributeValues": {
                        ":userId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.BETWEEN:
                if sort_key2:
                    return {
                        "TableName": cls.get_table(),
                        "IndexName": cls.get_table() + "GSI1",
                        "KeyConditionExpression": "userId = :userId AND createdAt BETWEEN :createdAt1 AND :createdAt2",
                        "ExpressionAttributeValues": {
                            ":userId": {"S": partition_key},
                            ":createdAt1": {"S": sort_key1},
                            ":createdAt2": {"S": sort_key2},
                        },
                        "ScanIndexForward": not reverse,
                        "Limit": limit,
                    }
                else:
                    return {}
            elif sort_op == SortKeyComparison.BEGINS_WITH:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI1",
                    "KeyConditionExpression": "userId = :userId AND begins_with ( createdAt, :createdAt )",
                    "ExpressionAttributeValues": {
                        ":userId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
        return {
            "TableName": cls.get_table(),
            "IndexName": cls.get_table() + "GSI1",
            "KeyConditionExpression": "userId = :userId",
            "ExpressionAttributeValues": {":userId": {"S": partition_key}},
            "ScanIndexForward": not reverse,
            "Limit": limit,
        }

    @classmethod
    def get_gs2_query(
        cls,
        partition_key: str,
        sort_op: SortKeyComparison | None = None,
        sort_key1: str | None = None,
        sort_key2: str | None = None,
        limit: int = 1,
        reverse: bool = False,
    ) -> dict:
        if sort_op and sort_key1:
            if sort_op == SortKeyComparison.EQ:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI2",
                    "KeyConditionExpression": "#reqId = :requestId AND createdAt = :createdAt",
                    "ExpressionAttributeNames": {"#reqId": "requestId"},
                    "ExpressionAttributeValues": {
                        ":requestId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                }
            elif sort_op == SortKeyComparison.LT:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI2",
                    "KeyConditionExpression": "#reqId = :requestId AND createdAt < :createdAt",
                    "ExpressionAttributeNames": {"#reqId": "requestId"},
                    "ExpressionAttributeValues": {
                        ":requestId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.LE:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI2",
                    "KeyConditionExpression": "#reqId = :requestId AND createdAt <= :createdAt",
                    "ExpressionAttributeNames": {"#reqId": "requestId"},
                    "ExpressionAttributeValues": {
                        ":requestId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.GT:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI2",
                    "KeyConditionExpression": "#reqId = :requestId AND createdAt > :createdAt",
                    "ExpressionAttributeNames": {"#reqId": "requestId"},
                    "ExpressionAttributeValues": {
                        ":requestId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.GE:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI2",
                    "KeyConditionExpression": "#reqId = :requestId AND createdAt >= :createdAt",
                    "ExpressionAttributeNames": {"#reqId": "requestId"},
                    "ExpressionAttributeValues": {
                        ":requestId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
            elif sort_op == SortKeyComparison.BETWEEN:
                if sort_key2:
                    return {
                        "TableName": cls.get_table(),
                        "IndexName": cls.get_table() + "GSI2",
                        "KeyConditionExpression": "#reqId = :requestId AND createdAt BETWEEN :createdAt1 AND :createdAt2",
                        "ExpressionAttributeNames": {"#reqId": "requestId"},
                        "ExpressionAttributeValues": {
                            ":requestId": {"S": partition_key},
                            ":createdAt1": {"S": sort_key1},
                            ":createdAt2": {"S": sort_key2},
                        },
                        "ScanIndexForward": not reverse,
                        "Limit": limit,
                    }
                else:
                    return {}
            elif sort_op == SortKeyComparison.BEGINS_WITH:
                return {
                    "TableName": cls.get_table(),
                    "IndexName": cls.get_table() + "GSI2",
                    "KeyConditionExpression": "#reqId = :requestId AND begins_with ( createdAt, :createdAt )",
                    "ExpressionAttributeNames": {"#reqId": "requestId"},
                    "ExpressionAttributeValues": {
                        ":requestId": {"S": partition_key},
                        ":createdAt": {"S": sort_key1},
                    },
                    "ScanIndexForward": not reverse,
                    "Limit": limit,
                }
        return {
            "TableName": cls.get_table(),
            "IndexName": cls.get_table() + "GSI2",
            "KeyConditionExpression": "#reqId = :requestId",
            "ExpressionAttributeNames": {"#reqId": "requestId"},
            "ExpressionAttributeValues": {":requestId": {"S": partition_key}},
            "ScanIndexForward": not reverse,
            "Limit": limit,
        }

    @classmethod
    def find(cls, query: dict, db_client=None):
        if not db_client:
            db_client = cls.new_db_client()
        res = db_client.query(**query)
        results = []
        if not res.get("Items"):
            return results
        for item in res["Items"]:
            _item = {}
            for _key, _value in item.items():
                for _, _subvalue in _value.items():
                    _item[_key] = _subvalue
                    break
            results.append(ChatGptRequestHistory(_item, db_client))
        return results

    def save(self):
        item = {}
        self.validate()
        json.loads(self._data["request"])  # Check JSON format
        properties = self._schema.get("properties", {})
        for key, value in properties.items():
            if value.get("type") == "string":
                item[key] = {"S": self._data.get(key)}
            elif value.get("type") == "number":
                item[key] = {"N": self._data.get(key)}
            elif value.get("type") == "boolean":
                item[key] = {"BOOL": self._data.get(key)}

        self._db_client.put_item(
            TableName=self.get_table(),
            Item=item,
        )

    def delete(self):
        self._db_client.delete_item(
            TableName=self.get_table(),
            Key={
                "talkRoomId": {"S": self._data.get("talkRoomId")},
                "createdAt": {"S": self._data.get("createdAt")},
            },
        )

    def get_response_message_content(self):
        if not self._data.get("response"):
            return None
        response = json.loads(self._data["response"])
        if not response:
            return None
        if not response.get("choices"):
            return None
        if len(response["choices"]) < 1:
            return None
        if not response["choices"][0].get("message"):
            return None
        return response["choices"][0]["message"].get("content")
