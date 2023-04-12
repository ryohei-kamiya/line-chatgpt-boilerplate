import os
import boto3


class DbClient:
    def __init__(self, *args, **argv):
        self._db_client = boto3.client("dynamodb", *args, **argv)

    def __getattr__(self, __name: str):
        return getattr(self._db_client, __name)

    @classmethod
    def get_client(cls, region_name: str | None = None, local: bool = False):
        if not region_name:
            region_name = os.getenv("REGION", "ap-northeast-1")
        if local:
            return DbClient(
                endpoint_url="http://127.0.0.1:8000",
                region_name=region_name,
                aws_access_key_id="fakeMyKeyId",
                aws_secret_access_key="fakeSecretAccessKey",
                aws_session_token="fakeSessionToken",
            )
        return DbClient(region_name=region_name)
