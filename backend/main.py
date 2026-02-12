from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import *
from auth import *
from rag import ask_rag, embeddings, VECTOR_INDEX_NAME
from db import pdf_collection, chat_collection, embeddings_collection
from pdf_loader import load_and_split_pdf
import shutil, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------
# Auth Routes
# -------------------------------
@app.post("/signup", response_model=Token)
def signup(user: UserCreate):
    from auth import create_hashed_password, create_access_token
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed = create_hashed_password(user.password)
    users_collection.insert_one({"email": user.email, "password": hashed})
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
def login(user: UserLogin):
    from auth import verify_password, create_access_token
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# -------------------------------
# PDF Upload & Embedding
# -------------------------------
@app.post("/upload_pdf")
def upload_pdf(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save PDF metadata
    pdf_collection.insert_one({
        "filename": file.filename,
        "path": file_path,
        "uploaded_by": current_user["email"]
    })

    # Process PDF and store embeddings
    pages = load_and_split_pdf(file_path)
    vectorstore = embeddings.from_documents(
        documents=pages,
        embedding=embeddings,
        collection=embeddings_collection,
        index_name=VECTOR_INDEX_NAME
    )

    return {"message": "PDF uploaded and embedded successfully", "file": file.filename}

# -------------------------------
# Chat Route
# -------------------------------
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    answer = ask_rag(req.message)
    chat_collection.insert_one({
        "user": current_user["email"],
        "question": req.message,
        "answer": answer
    })
    return {"reply": answer}

# -------------------------------
# Get chat history
# -------------------------------
@app.get("/chat_history")
def chat_history(current_user=Depends(get_current_user)):
    chats = chat_collection.find({"user": current_user["email"]})
    return [{"question": c["question"], "answer": c["answer"]} for c in chats]
