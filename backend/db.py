from pymongo import MongoClient
from pymongo.errors import OperationFailure
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI must be set in .env file")

client = MongoClient(MONGO_URI)
db = client["rag"]

# Collections
users_collection = db["users"]
chat_collection = db["chat_history"]
pdf_collection = db["pdfs"]
embeddings_collection = db["embeddings"]  # Vector embeddings for RAG

# Create indexes safely
try:
    users_collection.create_index("email", unique=True)
except OperationFailure as e:
    if "Index already exists" in str(e):
        print("⚠️  users_collection email index already exists, skipping creation.")
    else:
        raise

try:
    chat_collection.create_index("user")
except OperationFailure:
    print("⚠️  chat_collection index creation failed, skipping.")

try:
    pdf_collection.create_index("uploaded_by")
except OperationFailure:
    print("⚠️  pdf_collection index creation failed, skipping.")

# MongoDB Atlas vector index name
VECTOR_INDEX_NAME = "vector_index"

print("✅ Database connected successfully")
