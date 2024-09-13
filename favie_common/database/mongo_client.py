"""
mongodb operation
"""

import os
from datetime import datetime

import motor.motor_asyncio
from bson import ObjectId


class AsyncMongoDBWrapper:
    """
    async mongodb wrapper
    """

    def __init__(
        self, user: str, password: str, host: str, app_name: str, db_name: str
    ):
        self.uri = f"mongodb+srv://{user}:{password}@{host}&appName={app_name}"
        self.client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
        self.db = self.client[db_name]

        self.read_client = motor.motor_asyncio.AsyncIOMotorClient(
            self.uri + "&readPreference=secondary"
        )
        self.read_db = self.read_client[db_name]

    # define function for creating collection
    async def create_collection(self, collection_name):
        """Asynchronously create a new collection."""
        if collection_name not in await self.db.list_collection_names():
            await self.db.create_collection(collection_name)

    async def create(self, collection_name, document):
        """Asynchronously create a new document in the specified collection."""
        collection = self.db[collection_name]
        document.update({"created_at": datetime.now(), "updated_at": datetime.now()})
        result = await collection.insert_one(document)
        return result.inserted_id

    async def create_many(self, collection_name, documents):
        """Asynchronously create multiple documents in the specified collection."""
        collection = self.db[collection_name]
        for document in documents:
            document.update(
                {"created_at": datetime.now(), "updated_at": datetime.now()}
            )
        result = await collection.insert_many(documents)
        return result.inserted_ids

    async def read(self, collection_name, query=None, skip=0, limit=0, sort=None):
        """Asynchronously read documents from the specified collection."""
        collection = self.db[collection_name]
        cursor = collection.find(query or {}).skip(skip).limit(limit)
        if sort:
            cursor.sort(sort)
        return [document async for document in cursor]

    async def read_one(self, collection_name, query=None):
        """Asynchronously read one document from the specified collection."""
        collection = self.db[collection_name]
        document = await collection.find_one(query or {})
        return document

    async def read_by_id(self, collection_name, object_id):
        """Asynchronously read a document by its ID."""
        collection = self.db[collection_name]
        document = await collection.find_one({"_id": ObjectId(object_id)})
        return document

    async def update(self, collection_name, query, update_values):
        """Asynchronously update documents in the specified collection."""
        collection = self.db[collection_name]
        result = await collection.update_many(
            query, {"$set": update_values, "$currentDate": {"updated_at": True}}
        )
        return result.modified_count

    async def upsert_document(self, collection_name, query, update_values):
        """
        Asynchronously update documents in the specified collection.
        Insert document if not exists.
        """
        collection = self.db[collection_name]
        result = await collection.update_one(
            query,
            {"$set": update_values},
            upsert=True,
        )
        return result.modified_count

    async def update_by_id(self, collection_name, object_id, update_values):
        """Asynchronously update a document by its ID."""
        collection = self.db[collection_name]
        result = await collection.update_one(
            {"_id": ObjectId(object_id)},
            {"$set": update_values, "$currentDate": {"updated_at": True}},
        )
        return result.modified_count

    async def replace_one(self, collection_name, query, document):
        """Asynchronously replace one document in the specified collection."""
        collection = self.db[collection_name]
        document.update({"updated_at": datetime.now()})
        result = await collection.replace_one(query, document)
        return result.modified_count

    async def delete(self, collection_name, query):
        """Asynchronously delete documents from the specified collection."""
        collection = self.db[collection_name]
        result = await collection.delete_many(query)
        return result.deleted_count

    async def delete_by_id(self, collection_name, object_id):
        """Asynchronously delete a document by its ID."""
        collection = self.db[collection_name]
        result = await collection.delete_one({"_id": ObjectId(object_id)})
        return bool(result.deleted_count)

    async def delete_collection(self, collection_name):
        """Asynchronously delete the specified collection."""
        await self.db.drop_collection(collection_name)

    async def close(self):
        """Close the MongoDB connection."""
        self.client.close()

    async def get_all(self, collection_name):
        """Get all documents from a collection."""
        collection = self.db[collection_name]
        cursor = collection.find()
        return [document async for document in cursor]

    async def get_total_count(self, collection_name, query=None):
        """Get the total number of documents in a collection."""
        collection = self.db[collection_name]
        count = await collection.count_documents(query or {})
        return count

    async def get_random_one(self, collection_name):
        """Get a random document from a collection."""
        collection = self.db[collection_name]
        cursor = collection.aggregate([{"$sample": {"size": 1}}])
        return await cursor.to_list(1)


mongo = AsyncMongoDBWrapper(
    user=os.getenv("MONGODB_USER"),
    password=os.getenv("MONGODB_PASSWORD"),
    host=os.getenv("MONGODB_HOST"),
    app_name=os.getenv("MONGODB_APP_NAME"),
    db_name=os.getenv("MONGODB_NAME"),
)
