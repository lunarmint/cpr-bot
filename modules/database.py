import logging
from typing import Any, Mapping

from pymongo import MongoClient
from pymongo.collection import Collection

from config import config

log = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        self.username = config["database"]["username"]
        self.password = config["database"]["password"]
        self.hostname = config["database"]["hostname"]
        self.port = config["database"]["port"]
        self.database_name = config["database"]["database_name"]

        if not all([self.hostname, self.port, self.username, self.password, self.database_name]):
            log.error("One or more database connection variables are missing.")
            raise SystemExit

        self.url = f"mongodb://{self.username}:{self.password}@{self.hostname}:{self.port}/{self.database_name}"
        self.client = MongoClient(self.url)

    def get_collection(self, collection: str) -> Collection[Mapping[str, Any] | Any]:
        client = self.client
        database = client[self.database_name]
        collection = database[collection]
        return collection
