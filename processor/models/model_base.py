import json
from abc import ABCMeta, abstractmethod
from typing import Any, List
from enum import Enum
from jsonschema import validate
from models.db_client import DbClient


class SortKeyComparison(Enum):
    EQ = 1  # a = b - true if the attribute a is equal to the value b
    LT = 2  # a < b - true if a is less than b
    LE = 3  # a <= b - true if a is less than or equal to b
    GT = 4  # a > b - true if a is greater than b
    GE = 5  # a >= b - true if a is greater than or equal to b
    BETWEEN = 6  # a BETWEEN b AND c - true if a is greater than or equal to b, and less than or equal to c.
    BEGINS_WITH = 7  # begins_with (a, substr) - true if the value of attribute a begins with a particular substring.


class ModelBase(object):
    __metaclass__ = ABCMeta

    def __init__(self, db_client: DbClient | None = None, local: bool = False):
        if not db_client:
            db_client = self.new_db_client(local=local)
        super().__setattr__("_db_client", db_client)
        super().__setattr__("_schema", {})
        super().__setattr__("_data", {})

    def __setattr__(self, __name: str, __value: Any):
        if __name == "_db_client":
            super().__setattr__(__name, __value)
        elif __name == "_schema":
            super().__setattr__(__name, __value)
        elif __name == "_data":
            super().__setattr__(__name, __value)
        else:
            self._data[__name] = __value  # type: ignore

    def __getattr__(self, __name: str) -> Any:
        return self._data.get(__name)  # type: ignore

    @classmethod
    def new_db_client(cls, local: bool = False) -> DbClient:
        return DbClient.get_client(local=local)

    @classmethod
    @abstractmethod
    def create_table(cls, db_client: DbClient | None = None, local: bool = False):
        pass

    @classmethod
    @abstractmethod
    def get_table(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_query(
        cls,
        partition_key: str,
        sort_op: SortKeyComparison | None = None,
        sort_key1: str | None = None,
        sort_key2: str | None = None,
        limit: int = 1,
        reverse: bool = False,
    ) -> dict:
        pass

    @classmethod
    @abstractmethod
    def find(cls, query: dict, db_client: DbClient | None = None) -> List["ModelBase"]:
        pass

    def serialize(self):
        return json.dumps(self._data, ensure_ascii=False, sort_keys=True)

    def get_db_client(self) -> DbClient:
        return self._db_client

    def validate(self):
        validate(instance=self._data, schema=self._schema)

    def get(self, field: str) -> Any:
        return self._data.get(field)

    def set(self, field: str, value: Any):
        self._data[field] = value

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def delete(self):
        pass
