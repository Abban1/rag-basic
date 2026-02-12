from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class PDFUpload(BaseModel):
    title: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
