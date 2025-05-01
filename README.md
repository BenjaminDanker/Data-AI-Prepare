# Data-AI-Prepare

A set of Python utilities for extracting, processing, and preparing text data from PDFs, web pages, and other sources, ready for AI/ML workflows and vector database ingestion.

## Scripts Overview

- **text_analyzer.py**
  - Reads PDF files and computes paragraph statistics.
  - Functions:
    - `read_pdf(file_path)`: Extract text from PDF.
    - `split_text(text)`: Split text into paragraphs.
    - `analyze_paragraphs(paragraphs, chunk_size, chunk_overlap)`: Compute avg, max, min, median lengths and recommend chunk sizes.
  - Usage: edit `FILE_PATH`, `CHUNK_SIZE`, `CHUNK_OVERLAP` in the `__main__` section and run:
    ```bash
    python text_analyzer.py
    ```

- **text_to_embeddings.py**
  - Splits text or PDF into chunks and generates embeddings via OpenAI.
  - Dependencies: `openai`, `python-dotenv`, `pdfplumber`, `chardet`, `numpy`.
  - Edit environment variables `OPENAI_API_KEY` in a `.env` file.
  - Usage:
    ```bash
    python text_to_embeddings.py --file path/to/file.txt --output-dir embeddings --format numpy
    ```

- **ulr_to_json.py**  
  *(Note: script name contains a typo `ulr_to_json.py`.)*
  - Fetches and parses webpages into JSON formatted for DataStax Astra DB.
  - Dependencies: `requests`, `beautifulsoup4`.
  - Example at bottom demonstrates processing a list of URLs.
  - Usage:
    ```bash
    python ulr_to_json.py
    ```

- **upload_astra.py**
  - Uploads structured JSON with embeddings and metadata to Astra DB.
  - Dependencies: `openai`, `astrapy`, `scikit-learn`, `numpy`.
  - Set `OPENAI_API_KEY` and `ASTRADB_API_KEY` in `.env`.
  - Usage:
    ```bash
    python upload_astra.py
    ```

- **url_to_csv.py**
  - Extracts webpages and saves rows into a single CSV for bulk ingest.
  - Dependencies: `requests`, `beautifulsoup4`.
  - Usage:
    ```bash
    python url_to_csv.py
    ```

- **url_to_text.py**
  - Extracts visible text from webpages, optionally leveraging `unstructured`.
  - Dependencies: `requests`, `beautifulsoup4`, optionally `unstructured`.
  - Configurable save directory and processed-URL tracking.
  - Usage:
    ```bash
    python url_to_text.py
    ```

## Prerequisites

- Python 3.7 or newer.
- Install required packages:
  ```bash
  pip install PyPDF2 PyMuPDF numpy requests beautifulsoup4 pdfplumber chardet python-dotenv openai astrapy scikit-learn
  # optional for url_to_text: pip install unstructured
  ```

## Usage

Modify hardcoded paths or environment variables in each script’s `__main__` section or call functions directly in your own modules.

## Contributing

Feel free to open issues or submit pull requests to improve functionality, add CLI flags, or correct script names.

## License

This project is licensed under the MIT [License](License).
