import functools
from typing import Dict

import pymongo
import random

from mongomock import ObjectId
from pymongo.results import InsertOneResult

from src.db_worker import get_client, insert_one
import pytest
from pymongo import MongoClient
import mongomock


@pytest.fixture
def mock_mongo():
    return mongomock.MongoClient()


servers = ["server.example.com", "server2.example.com"]
ports = [27017, 27024]
sockets = tuple(zip(servers, ports))


@pytest.fixture
def test_data() -> Dict:
    return random.choice(
        [
            {
                "name": "Temp name 1",
                "parameters": {"location": "Innopolis", "value": 7},
            },
            {
                "name": "Temp name 2",
                "parameters": {"location": "Innopolis", "value": 3},
            },
            {"name": "Temp name 3", "parameters": {"location": "Kazan", "value": 7}},
            {"name": "Temp name 4", "parameters": {"location": "Kazan", "value": 5}},
        ]
    )


def my_params(func):
    @functools.wraps(func)
    @pytest.mark.parametrize("server_name", servers)
    @pytest.mark.parametrize("port", ports)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapped


class TestBasicConnection:
    @my_params
    def test_client_connection(self, server_name, port):
        client1 = get_client(server_name, port)
        assert isinstance(client1, MongoClient)

    @my_params
    def test_multiple_clients(self, server_name, port):
        client1 = get_client(server_name, port)
        assert get_client(server_name, port) is client1

    @my_params
    @mongomock.patch(servers=sockets)
    def test_creating_db_and_collections(self, server_name, port, test_data):
        db_names = [f"test_db_{i}" for i in range(4)]
        collection_names = [f"collection_{i}" for i in range(3)]
        client = mongomock.MongoClient(server_name, port)
        for db in db_names:
            for coll in collection_names:
                insert_one(client, test_data, db_name=db, collection_name=coll)
        assert client.list_database_names() == db_names
        for db in db_names:
            assert getattr(client, db).list_collection_names() == collection_names

    @my_params
    @mongomock.patch(servers=sockets)
    def test_insert_one(self, server_name, port, test_data):
        client = mongomock.MongoClient(server_name, port)
        test_data['_id'] = ObjectId()
        doc = insert_one(client, test_data)
        assert isinstance(doc, InsertOneResult)
        assert doc.acknowledged
        assert doc.inserted_id == test_data['_id']

    @my_params
    @mongomock.patch(servers=sockets)
    def test_find_one(self, server_name, port, test_data):
        client = mongomock.MongoClient(server_name, port)

        doc = insert_one(client, test_data)
        assert find_one(client, test_data)['_id'] == doc.inserted_id

        test_data.update({
            '_id': ObjectId(doc.inserted_id)
        })
        assert find_one(client, test_data) == test_data
        assert find_one(client, {'_id': doc.inserted_id}) == test_data
        assert find_one(client, {'_id': str(doc.inserted_id)}) is None
        assert find_one(client, {'name': test_data['name']}) == test_data
