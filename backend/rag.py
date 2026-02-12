import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages

from pymongo import MongoClient

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.tools import tool
from groq import Groq

from pdf_loader import load_and_split_pdf

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")
if not MONGO_URI:
    raise ValueError("MONGO_URI not found in .env")

# -------------------------------
# PDF and embeddings
# -------------------------------
PDF_PATH = "data/document.pdf"
pages_split = load_and_split_pdf(PDF_PATH)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

# -------------------------------
# MongoDB Atlas vector search
# -------------------------------
DB_NAME = "rag"
COLLECTION_NAME = "embeddings"
INDEX_NAME = "vector_index"

# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

# Create vectorstore
vectorstore = MongoDBAtlasVectorSearch.from_documents(
    documents=pages_split,
    embedding=embeddings,
    collection=collection,  # Must pass pymongo Collection object
    index_name=INDEX_NAME   # Must match Atlas vector index
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

# -------------------------------
# Retriever tool
# -------------------------------
@tool
def retriever_tool(query: str) -> str:
    """
    Search the uploaded PDF documents for relevant information.
    """
    docs = retriever.invoke(query)
    
    if not docs:
        return "No relevant content found in the PDF."
    
    return "\n\n".join(doc.page_content for doc in docs)

# -------------------------------
# Groq LLM wrapper
# -------------------------------
class GroqLLM:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def invoke(self, messages: list):
        groq_messages = []
        for m in messages:
            role = "system" if isinstance(m, SystemMessage) else "user"
            groq_messages.append({"role": role, "content": m.content})

        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.7,
            messages=groq_messages
        )
        return HumanMessage(content=response.choices[0].message.content)

# Initialize LLM
llm = GroqLLM(api_key=GROQ_API_KEY)

# -------------------------------
# RAG agent workflow
# -------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def call_llm(state: AgentState) -> dict:
    messages = list(state["messages"])
    user_query = messages[-1].content

    # Get context from PDF via vector search
    context = retriever_tool.invoke(user_query)

    system_prompt = (
        "You are an expert answer giver who reads PDF files. "
        "Use ONLY the provided context to answer.\n\n"
        f"CONTEXT:\n{context}"
    )

    # Combine system prompt with conversation messages
    prompt = [SystemMessage(content=system_prompt)] + messages

    # Call LLM
    response = llm.invoke(prompt)

    return {"messages": [response]}

# Create workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_llm)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

rag_agent = workflow.compile()

# -------------------------------
# Main RAG function
# -------------------------------
def ask_rag(question: str) -> str:
    """
    Ask a question and get a response from RAG agent.
    """
    result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content
