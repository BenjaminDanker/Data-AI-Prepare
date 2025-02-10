import PyPDF2
import fitz  # PyMuPDF
import numpy as np
import re

def read_pdf(file_path):
    """Reads text from a PDF file using PyMuPDF for better text extraction."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text

def split_text(text):
    """Splits text into paragraphs using improved regex-based splitting."""
    paragraphs = re.split(r'\n\s*\n+', text)  # Splits on multiple newlines
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    return paragraphs

def analyze_paragraphs(paragraphs, chunk_size=512, chunk_overlap=128):
    """Analyzes paragraph lengths and determines optimal chunk settings."""
    paragraph_lengths = [len(p) for p in paragraphs]
    
    # Statistics
    avg_length = np.mean(paragraph_lengths)
    max_length = np.max(paragraph_lengths)
    min_length = np.min(paragraph_lengths)
    median_length = np.median(paragraph_lengths)
    
    # Count paragraphs exceeding chunk size
    exceeding_count = sum(1 for l in paragraph_lengths if l > chunk_size)
    
    # Recommend chunk size based on distribution
    recommended_chunk_size = int(np.percentile(paragraph_lengths, 90))
    recommended_overlap = int(recommended_chunk_size * 0.25)
    
    return {
        "avg_length": avg_length,
        "max_length": max_length,
        "min_length": min_length,
        "median_length": median_length,
        "paragraphs_exceeding_chunk_size": exceeding_count,
        "recommended_chunk_size": recommended_chunk_size,
        "recommended_chunk_overlap": recommended_overlap
    }

if __name__ == "__main__":
    # Hardcoded values for chunk size and overlap
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 128
    FILE_PATH = "data_pdf/All_Data.pdf"  # Replace with your PDF file path
    
    text = read_pdf(FILE_PATH)
    paragraphs = split_text(text)
    results = analyze_paragraphs(paragraphs, CHUNK_SIZE, CHUNK_OVERLAP)
    
    # Debugging: Print top 5 longest paragraphs
    print("Top 5 longest paragraphs:")
    for p in sorted(paragraphs, key=len, reverse=True)[:5]:
        print(len(p), ":", p[:100])  # Show first 100 chars
    
    # Display results
    print("Analysis Results:")
    for key, value in results.items():
        print(f"{key}: {value}")
