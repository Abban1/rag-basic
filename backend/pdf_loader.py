import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_and_split_pdf(pdf_path: str):
    """
    Load a PDF file and split it into chunks for embedding.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of document chunks
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Load PDF
    loader = PyMuPDFLoader(pdf_path)
    pages = loader.load()
    
    if not pages:
        raise ValueError("PDF appears to be empty or unreadable")

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = splitter.split_documents(pages)
    
    print(f"✅ Loaded PDF: {len(pages)} pages, split into {len(chunks)} chunks")
    
    return chunks