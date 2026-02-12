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
from db import embeddings_collection, VECTOR_INDEX_NAME

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

# -------------------------------
# Initialize embeddings
# -------------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

# -------------------------------
# MongoDB Atlas vector search
# -------------------------------
vectorstore = MongoDBAtlasVectorSearch(
    collection=embeddings_collection,
    embedding=embeddings,
    index_name=VECTOR_INDEX_NAME
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# -------------------------------
# Retriever tool
# -------------------------------
@tool
def retriever_tool(query: str) -> str:
    """
    Search the uploaded PDF documents for relevant information.
    """
    try:
        docs = retriever.invoke(query)
        
        if not docs:
            return "No relevant content found in the uploaded PDFs. Please upload a PDF document first."
        
        # Combine and deduplicate results
        content = "\n\n".join([
            f"[Source {i+1}]\n{doc.page_content}" 
            for i, doc in enumerate(docs)
        ])
        
        return content
    except Exception as e:
        return f"Error retrieving information: {str(e)}"


# -------------------------------
# Groq LLM wrapper
# -------------------------------
class GroqLLM:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def invoke(self, messages: list):
        groq_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                role = "system"
            elif isinstance(m, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            groq_messages.append({"role": role, "content": m.content})

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=1024,
                messages=groq_messages
            )
            return HumanMessage(content=response.choices[0].message.content)
        except Exception as e:
            return HumanMessage(content=f"Error generating response: {str(e)}")

# Initialize LLM
llm = GroqLLM(api_key=GROQ_API_KEY)

# -------------------------------
# RAG agent workflow
# -------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def call_llm(state: AgentState) -> dict:
    """
    Process user query using RAG (Retrieval Augmented Generation).
    """
    messages = list(state["messages"])
    user_query = messages[-1].content

    # Retrieve relevant context from PDFs
    context = retriever_tool.invoke(user_query)

    # Create system prompt with context
    system_prompt = (
        "You are an intelligent assistant that answers questions based on PDF documents.\n\n"
        "INSTRUCTIONS:\n"
        "1. Use ONLY the provided context to answer the question\n"
        "2. If the context doesn't contain relevant information, say so clearly\n"
        "3. Be concise but thorough\n"
        "4. If you're unsure, acknowledge the uncertainty\n"
        "5. Cite specific parts of the context when possible\n\n"
        f"CONTEXT FROM UPLOADED PDFS:\n{context}\n\n"
        "Now answer the user's question based on this context."
    )

    # Build prompt with system message and conversation history
    prompt = [SystemMessage(content=system_prompt)] + messages
    
    # Generate response
    response = llm.invoke(prompt)
    return {"messages": [response]}

# Build workflow graph
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
    Ask a question and get an answer based on uploaded PDFs.
    
    Args:
        question: User's question
        
    Returns:
        AI-generated answer based on PDF content
    """
    try:
        result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})
        return result["messages"][-1].content
    except Exception as e:
        return f"I encountered an error while processing your question: {str(e)}"

print("✅ RAG system initialized successfully")