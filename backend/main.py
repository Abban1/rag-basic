from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import *
from auth import *
from rag import ask_rag, embeddings, VECTOR_INDEX_NAME
from db import pdf_collection, chat_collection, embeddings_collection
from pdf_loader import load_and_split_pdf
from langchain_mongodb import MongoDBAtlasVectorSearch
import shutil, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------
# Auth Routes
# -------------------------------
@app.post("/signup", response_model=Token)
def signup(user: UserCreate):
    from auth import create_hashed_password, create_access_token
    
    # Validate password length
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
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
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/verify_token")
def verify_token(current_user=Depends(get_current_user)):
    """Verify if the token is still valid"""
    return {"valid": True, "email": current_user["email"]}

# -------------------------------
# PDF Upload & Embedding
# -------------------------------
@app.post("/upload_pdf")
def upload_pdf(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (e.g., max 10MB)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()  # Get size
    file.file.seek(0)  # Reset to beginning
    
    if file_size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
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
        
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
        
        vectorstore = MongoDBAtlasVectorSearch.from_documents(
            documents=pages,
            embedding=embeddings_model,
            collection=embeddings_collection,
            index_name=VECTOR_INDEX_NAME
        )

        return {
            "message": f"PDF '{file.filename}' uploaded and embedded successfully",
            "file": file.filename,
            "chunks": len(pages)
        }
    except Exception as e:
        # Clean up file if processing failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

# -------------------------------
# Chat Route
# -------------------------------
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        answer = ask_rag(req.message)
        chat_collection.insert_one({
            "user": current_user["email"],
            "question": req.message,
            "answer": answer
        })
        return {"reply": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

# -------------------------------
# Get chat history
# -------------------------------
@app.get("/chat_history")
def chat_history(current_user=Depends(get_current_user)):
    try:
        chats = chat_collection.find({"user": current_user["email"]}).sort("_id", -1).limit(50)
        return [{"question": c["question"], "answer": c["answer"]} for c in chats]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat history: {str(e)}")

# -------------------------------
# Health check
# -------------------------------
@app.get("/")
def health_check():
    return {"status": "ok", "message": "PDF RAG Chat API is running"}