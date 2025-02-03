import os
import openai
import time
from dotenv import load_dotenv
import numpy as np
import csv
import json
import pdfplumber  # For PDF text extraction
import chardet      # For encoding detection
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAIError, RateLimitError, APIConnectionError, APIError

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

if not client.api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

def detect_encoding(file_path, num_bytes=10000):
    """
    Detects the encoding of a file using chardet.
    
    Args:
        file_path (str): Path to the file.
        num_bytes (int): Number of bytes to read for detection.
    
    Returns:
        str: Detected encoding or 'utf-8' as default.
    """
    try:
        with open(file_path, 'rb') as f:
            rawdata = f.read(num_bytes)
        result = chardet.detect(rawdata)
        encoding = result['encoding']
        confidence = result['confidence']
        if encoding and confidence > 0.5:
            return encoding
        else:
            print(f"Low confidence in encoding detection for {file_path}. Defaulting to 'utf-8'.")
            return 'utf-8'
    except Exception as e:
        print(f"Error detecting encoding for {file_path}: {e}. Defaulting to 'utf-8'.")
        return 'utf-8'

def split_text_into_chunks(text, separator="\n\n", chunk_size=1000, overlap=100):
    """
    Splits the input text into chunks based on a specified separator with defined overlap.
    
    Args:
        text (str): The text to be split.
        separator (str): The delimiter used to split the text (e.g., "\n\n", ".", etc.).
        chunk_size (int): Approximate number of tokens per chunk.
        overlap (int): Number of overlapping tokens between chunks.
    
    Returns:
        List[str]: A list of text chunks.
    """
    # Split the text based on the specified separator
    segments = text.split(separator)
    chunks = []
    current_chunk = ""
    current_length = 0

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue  # Skip empty segments
        segment_length = len(segment.split())  # Using word count as a proxy for tokens
        if current_length + segment_length > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Start a new chunk with overlap
            current_chunk_words = current_chunk.split()
            if overlap > 0 and len(current_chunk_words) >= overlap:
                overlap_words = ' '.join(current_chunk_words[-overlap:])
            else:
                overlap_words = ' '.join(current_chunk_words)
            current_chunk = overlap_words + " " + segment
            current_length = len(current_chunk.split())
        else:
            if current_chunk:
                current_chunk += " " + segment
            else:
                current_chunk = segment
            current_length += segment_length

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def extract_text_from_pdf(file_path):
    """
    Extracts text from a PDF file using pdfplumber.
    
    Args:
        file_path (str): Path to the PDF file.
    
    Returns:
        str: Extracted text content.
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"  # Maintain paragraph separation
    except Exception as e:
        print(f"Error extracting text from PDF {file_path}: {e}")
    return text

def generate_embeddings_for_chunk(chunk, model="text-embedding-3-large", retries=3, backoff_factor=2):
    """
    Generates embeddings for a single text chunk using OpenAI's API with retry logic.
    
    Args:
        chunk (str): The text chunk to embed.
        model (str): The OpenAI model to use for embedding.
        retries (int): Number of retry attempts.
        backoff_factor (int or float): Multiplier for sleep time between retries.
    
    Returns:
        List[float] or None: The embedding vector or None if failed.
    """
    for attempt in range(1, retries + 1):
        try:
            response = client.embeddings.create(
                input=chunk,
                model=model
            )
            if response and hasattr(response, 'data') and response.data:
                return response.data[0].embedding
            else:
                raise ValueError("Invalid response structure from OpenAI API.")
        except RateLimitError:
            print(f"Rate limit exceeded. Attempt {attempt} of {retries}. Retrying in {backoff_factor} seconds...")
            time.sleep(backoff_factor)
        except APIConnectionError:
            print(f"API connection error. Attempt {attempt} of {retries}. Retrying in {backoff_factor} seconds...")
            time.sleep(backoff_factor)
        except APIError as e:
            print(f"API error: {e}. Attempt {attempt} of {retries}. Retrying in {backoff_factor} seconds...")
            time.sleep(backoff_factor)
        except OpenAIError as e:
            print(f"OpenAI error: {e}. Attempt {attempt} of {retries}. Retrying in {backoff_factor} seconds...")
            time.sleep(backoff_factor)
        except Exception as e:
            print(f"Unexpected error: {e}. Attempt {attempt} of {retries}. Retrying in {backoff_factor} seconds...")
            time.sleep(backoff_factor)
    print("Failed to generate embedding after multiple attempts.")
    return None

def save_embeddings(embeddings, output_file, save_as):
    """
    Saves embeddings to the specified file format.
    
    Args:
        embeddings (List[List[float]]): List of embedding vectors.
        output_file (str): Path to the output file.
        save_as (str): Format to save embeddings ('npy', 'csv', or 'json').
    """
    try:
        if save_as == 'npy':
            np.save(output_file, embeddings)
            print(f"Embeddings saved to {output_file}")
        elif save_as == 'csv':
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(embeddings)
            print(f"Embeddings saved to {output_file}")
        elif save_as == 'json':
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(embeddings, jsonfile)
            print(f"Embeddings saved to {output_file}")
        else:
            print(f"Unsupported save format: {save_as}. Skipping saving embeddings.")
    except Exception as e:
        print(f"Error saving embeddings to {output_file}: {e}")

def process_file(file_path, embeddings_dir, save_as='npy', separator="\n\n", chunk_size=1000, overlap=100):
    """
    Processes a single text or PDF file: reads content, splits into chunks, generates embeddings,
    and saves them.
    
    Args:
        file_path (str): Path to the input file.
        embeddings_dir (str): Directory to save the embeddings.
        save_as (str): Format to save embeddings ('npy', 'csv', or 'json').
        separator (str): The delimiter used to split the text.
        chunk_size (int): Approximate number of tokens per chunk.
        overlap (int): Number of overlapping tokens between chunks.
    
    Returns:
        int: Number of embeddings generated.
    """
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        # Determine embedding file path based on save format
        if save_as == 'npy':
            embedding_file = os.path.join(embeddings_dir, f"{base_filename}_embeddings.npy")
        elif save_as == 'csv':
            embedding_file = os.path.join(embeddings_dir, f"{base_filename}_embeddings.csv")
        elif save_as == 'json':
            embedding_file = os.path.join(embeddings_dir, f"{base_filename}_embeddings.json")
        else:
            print(f"Unsupported save format: {save_as}. Skipping saving embeddings.")
            embedding_file = None

        # Check if embedding already exists to avoid redundant processing
        if embedding_file and os.path.exists(embedding_file):
            print(f"Embeddings for {base_filename} already exist. Skipping.")
            return 0

        # Extract text based on file type
        if file_extension == '.txt':
            encoding = detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                text = f.read()
        elif file_extension == '.pdf':
            text = extract_text_from_pdf(file_path)
            if not text.strip():
                print(f"No text extracted from PDF {file_path}. Skipping.")
                return 0
        else:
            print(f"Unsupported file type {file_extension} for file {file_path}. Skipping.")
            return 0

        # Split text into chunks
        chunks = split_text_into_chunks(text, separator=separator, chunk_size=chunk_size, overlap=overlap)
        embeddings = []
        start_time = time.time()

        for i, chunk in enumerate(chunks):
            embedding = generate_embeddings_for_chunk(chunk)
            if embedding:
                embeddings.append(embedding)
                print(f"Processed chunk {i+1}/{len(chunks)} for file {os.path.basename(file_path)}")
            else:
                print(f"Skipping chunk {i+1} for file {os.path.basename(file_path)} due to previous errors.")

        end_time = time.time()
        total_time = end_time - start_time
        print(f"Generated {len(embeddings)} embeddings for {os.path.basename(file_path)} in {total_time:.2f} seconds.")

        # Save embeddings
        if embedding_file:
            save_embeddings(embeddings, embedding_file, save_as)

        return len(embeddings)

    except Exception as e:
        print(f"Failed to process file {file_path}: {e}")
        return 0

def generate_embeddings_from_folder(completed_dir='Complete', embeddings_dir='Embeddings', save_as='npy',
                                   separator="\n\n", chunk_size=1000, overlap=100, max_workers=5):
    """
    Processes all text and PDF files in the completed directory to generate embeddings using parallel processing.
    
    Args:
        completed_dir (str): Directory containing input files.
        embeddings_dir (str): Directory to save the embeddings.
        save_as (str): Format to save embeddings ('npy', 'csv', or 'json').
        separator (str): The delimiter used to split the text.
        chunk_size (int): Approximate number of tokens per chunk.
        overlap (int): Number of overlapping tokens between chunks.
        max_workers (int): Number of parallel threads.
    
    Returns:
        None
    """
    if not os.path.exists(completed_dir):
        raise FileNotFoundError(f"The directory '{completed_dir}' does not exist.")

    if not os.path.exists(embeddings_dir):
        os.makedirs(embeddings_dir)
        print(f"Created embeddings directory at '{embeddings_dir}'.")

    # List all .txt and .pdf files in the completed directory
    text_files = [file for file in os.listdir(completed_dir) if file.lower().endswith(('.txt', '.pdf'))]

    if not text_files:
        print(f"No text or PDF files found in '{completed_dir}'.")
        return

    total_files = len(text_files)
    total_embeddings = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_file, os.path.join(completed_dir, file), embeddings_dir, save_as,
                            separator, chunk_size, overlap): file
            for file in text_files
        }

        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                embeddings_count = future.result()
                total_embeddings += embeddings_count
            except Exception as e:
                print(f"Error processing file {file}: {e}")

    print(f"Processed {total_files} files with a total of {total_embeddings} embeddings.")

if __name__ == "__main__":
    # Configuration: Set the desired format and separator here
    # npy is a file type for saving numpy arrays
    # csv and json for saving structured data, separate from unstructured txt such as paragraphs
    SAVE_FORMAT = 'json'           # Options: 'npy', 'csv', 'json'
    SEPARATOR = "\n\n"            # Options: "\n\n", ".", "END_OF_SECTION", etc.

    # Directories
    COMPLETED_DIR = 'Complete'      # Ensure this directory exists and contains .txt and/or .pdf files
    EMBEDDINGS_DIR = 'Embeddings'   # Embeddings will be saved here

    # Processing Parameters
    CHUNK_SIZE = 1000     # Adjust based on your needs and model token limits
    OVERLAP = 100         # Number of overlapping tokens between chunks
    MAX_WORKERS = 5       # Number of parallel threads (adjust based on your system and API rate limits)

    generate_embeddings_from_folder(
        completed_dir=COMPLETED_DIR,
        embeddings_dir=EMBEDDINGS_DIR,
        save_as=SAVE_FORMAT,
        separator=SEPARATOR,
        chunk_size=CHUNK_SIZE,
        overlap=OVERLAP,
        max_workers=MAX_WORKERS
    )
