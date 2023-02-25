import logging
import urllib.parse
from typing import Any, Mapping

from pymongo import MongoClient
from pymongo.collection import Collection

from modules.utils.config import config

log = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        # Username and password must be escaped according to RFC 3986, use urllib.parse.quote_plus.
        self.username = urllib.parse.quote_plus(config["database"]["username"].as_str_expanded())
        self.password = urllib.parse.quote_plus(config["database"]["password"].as_str_expanded())
        self.hostname = config["database"]["hostname"].as_str_expanded()
        self.port = config["database"]["port"].as_str_expanded()
        self.database_name = config["database"]["database_name"].as_str_expanded()

        if not all([self.hostname, self.port, self.username, self.password, self.database_name]):
            log.error("One or more database connection variables are missing.")
            raise SystemExit

        self.url = f"mongodb://{self.username}:{self.password}@{self.hostname}:{self.port}/?authSource={self.database_name}"
        self.client = MongoClient(self.url)

    def get_collection(self, collection: str) -> Collection[Mapping[str, Any] | Any]:
        client = self.client
        database = client[self.database_name]
        collection = database[collection]
        return collection
