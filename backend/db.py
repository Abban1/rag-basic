from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["rag"]

# Collections
users_collection = db["users"]
chat_collection = db["chat_history"]
pdf_collection = db["pdfs"]
embeddings_collection = db["embeddings"]  # Vector embeddings for RAG

# MongoDB Atlas vector index name
VECTOR_INDEX_NAME = "vector_index"
