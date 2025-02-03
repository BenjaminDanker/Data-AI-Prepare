"""
Parse out text, links, images, and more from multiple HTML files.
Modified from extract.py in https://github.com/fephsun/dialup.
For example:
    from urltotext import ParsedWebpage
    urls = [
        "http://en.wikipedia.org/wiki/Frog",
        "https://www.example.com",
        # Add more URLs as needed
    ]
    process_multiple_webpages(urls, "compiled_webpages.txt")
"""
import re
from typing import Optional
import requests
from bs4 import BeautifulSoup, Comment
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log only to console
    ]
)
logger = logging.getLogger(__name__)


class ParsedWebpage:
    def __init__(self, url: str):
        self.url: str = url
        self.html: str = ""
        self.soup: Optional[BeautifulSoup] = None
        self.title: Optional[str] = None
        self.text: str = ""

        self._fetch_html()
        if self.html:
            self._parse_html()
            self._process_html()

    def _fetch_html(self) -> None:
        """Fetch the raw HTML content from the URL."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; WebScraper/1.0; +http://yourwebsite.com/bot)"
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            self.html = response.text
            logger.info(f"Successfully fetched content from {self.url}")
        except requests.RequestException as e:
            logger.error(f"Error fetching {self.url}: {e}")
            self.html = ""

    def _parse_html(self) -> None:
        """Parse the raw HTML using BeautifulSoup."""
        self.soup = BeautifulSoup(self.html, "html.parser")
        logger.info("Parsed HTML content with BeautifulSoup")

    def _process_html(self) -> None:
        """Clean and extract desired content from the HTML."""
        if not self.soup:
            logger.warning("No BeautifulSoup object to process")
            return

        # Remove unwanted tags (excluding 'footer' to include footer content)
        unwanted_tags = ["script", "style", "form", "nav", "header", "aside"]
        for tag in self.soup.find_all(unwanted_tags):
            tag.decompose()
        logger.info(f"Removed tags: {unwanted_tags}")

        # Remove comments
        for comment in self.soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        logger.info("Removed comments from HTML")

        # Replace <img> tags with descriptive text
        self._replace_images()

        # Extract the title
        if self.soup.title and self.soup.title.string:
            self.title = self.soup.title.string.strip()
            logger.info(f"Extracted title: {self.title}")
        else:
            logger.warning("No title found in the HTML")

        # Extract visible text with preserved newlines
        self.text = self._extract_text()
        logger.info("Extracted text from HTML")

    def _replace_images(self) -> None:
        """Replace <img> tags with descriptive alt text."""
        for img in self.soup.find_all("img"):
            # Customize based on image attributes
            alt_text = img.get("alt", "").strip()
            src = img.get("src", "").strip()
            description = "An image"
            if alt_text:
                description += f" of {alt_text}"
            elif src:
                description += f" from {src}"
            else:
                description += "."

            replacement = f"{description}. "
            img.replace_with(replacement)
        logger.info("Replaced <img> tags with descriptive text")

    def _extract_text(self) -> str:
        """Extract and clean visible text from the HTML, preserving newlines and removing © symbols."""
        # Initialize an empty list to hold lines of text
        lines = []

        # Define block-level tags that should introduce newlines
        block_tags = {
            "p", "div", "section", "article", "header", "footer",
            "nav", "aside", "h1", "h2", "h3", "h4", "h5", "h6", "li"
        }

        for element in self.soup.descendants:
            if getattr(element, 'name', None) in block_tags:
                # Add a newline before block-level elements
                lines.append("\n")
            if isinstance(element, str):
                # Strip leading/trailing whitespaces and reduce multiple spaces to single
                text = ' '.join(element.split())
                if text:
                    lines.append(text + " ")

        # Join the lines and split by newlines to handle them properly
        raw_text = ''.join(lines)
        # Replace multiple newlines with a single newline
        cleaned_text = re.sub(r'\n+', '\n', raw_text)
        # Strip leading/trailing whitespaces on each line
        cleaned_lines = [line.strip() for line in cleaned_text.split('\n')]
        # Remove empty lines
        final_text = '\n'.join([line for line in cleaned_lines if line])

        # Remove © symbols and any following text (e.g., © 2025)
        final_text = re.sub(r'©\s*\d{0,4}', '', final_text)

        return final_text

    def save_to_txt(self, directory: Optional[Path] = None, filename: Optional[str] = None) -> None:
        """
        Save the extracted text to a TXT file in the specified directory.

        :param directory: Optional; Path object representing the directory to save the document. Defaults to a folder within the project directory.
        :param filename: Optional; name of the TXT file. If not provided, defaults to the sanitized title or derived from the URL.
        """
        # Determine the save directory
        if directory is None:
            # Create a folder named 'webpage_data' inside the project directory
            project_dir = Path.cwd()
            directory = project_dir / "webpage_data"
        else:
            directory = Path(directory)

        # Ensure the save directory exists
        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                return

        # Set default filename if not provided
        if not filename:
            # Sanitize the title to create a valid filename
            if self.title:
                sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", self.title)
                filename = f"{sanitized_title}.txt"
            else:
                # Fallback to using the URL's domain and path
                parsed_url = urlparse(self.url)
                path = parsed_url.path.strip("/").replace("/", "_")
                if path:
                    filename = f"{parsed_url.netloc}_{path}.txt"
                else:
                    filename = f"{parsed_url.netloc}.txt"

        # Full path to the output file
        file_path = directory / filename

        # Prepare the content to write
        content = ""
        if self.title:
            content += f"{self.title}\n"
            content += f"{self.url}\n\n"
        else:
            content += f"{self.url}\n\n"
        content += self.text

        try:
            # Write the content to the TXT file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"File saved successfully at {file_path}")
        except Exception as e:
            logger.error(f"Failed to save file at {file_path}: {e}")


def read_processed_urls(file_path: Path) -> set:
    """
    Read the processed URLs from a file and return them as a set.

    :param file_path: Path object representing the 'processed_urls.txt' file.
    :return: Set of processed URLs.
    """
    if not file_path.exists():
        logger.info(f"Processed URLs file not found at {file_path}. A new one will be created.")
        return set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            processed = {line.strip() for line in f if line.strip()}
        logger.info(f"Loaded {len(processed)} processed URLs from {file_path}")
        return processed
    except Exception as e:
        logger.error(f"Failed to read processed URLs from {file_path}: {e}")
        return set()


def append_processed_url(file_path: Path, url: str) -> None:
    """
    Append a processed URL to the 'processed_urls.txt' file.

    :param file_path: Path object representing the 'processed_urls.txt' file.
    :param url: The URL to append.
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
        logger.info(f"Appended URL to {file_path}: {url}")
    except Exception as e:
        logger.error(f"Failed to append URL to {file_path}: {e}")


def process_multiple_webpages(urls: list, output_directory: Optional[str] = None, processed_file: Optional[str] = None) -> None:
    """
    Process multiple URLs and save each extracted content into its own TXT file.
    Skips URLs that have already been processed as per the 'processed_urls.txt' file.

    :param urls: List of webpage URLs to parse.
    :param output_directory: Optional; Path to the directory where documents will be saved. Defaults to a 'webpage_data' folder inside the project directory.
    :param processed_file: Optional; Path to the 'processed_urls.txt' file. Defaults to 'processed_urls.txt' in the project directory.
    """
    # Determine the save directory
    if output_directory:
        save_dir = Path(output_directory)
    else:
        # Create a folder named 'webpage_txts' inside the project directory
        save_dir = Path.cwd() / "webpage_data"

    # Determine the processed URLs file path
    if processed_file:
        processed_file_path = Path(processed_file)
    else:
        # Default to 'processed_urls.txt' in the project directory
        processed_file_path = Path.cwd() / "processed_urls.txt"

    # Load already processed URLs
    processed_urls = read_processed_urls(processed_file_path)

    # Ensure the save directory exists
    if not save_dir.exists():
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {save_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory {save_dir}: {e}")
            return

    # Remove duplicate URLs from the input list
    unique_urls = list(set(urls))
    logger.info(f"Total unique URLs to process: {len(unique_urls)}")

    # Iterate over each URL
    for idx, url in enumerate(unique_urls, start=1):
        if url in processed_urls:
            logger.info(f"URL already processed and skipped ({idx}/{len(unique_urls)}): {url}")
            continue  # Skip already processed URLs

        logger.info(f"Processing URL {idx}/{len(unique_urls)}: {url}")
        webpage = ParsedWebpage(url)

        if not webpage.title and not webpage.text:
            logger.warning(f"No content extracted from {url}. Skipping.")
            continue  # Do not mark as processed if no content was extracted

        # Determine a filename for the document
        if webpage.title:
            # Sanitize the title to create a valid filename
            sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", webpage.title)
            filename = f"{sanitized_title}.txt"
        else:
            # Fallback to using the URL's domain and path
            parsed_url = urlparse(webpage.url)
            path = parsed_url.path.strip("/").replace("/", "_")
            if path:
                filename = f"{parsed_url.netloc}_{path}.txt"
            else:
                filename = f"{parsed_url.netloc}.txt"

        # Save the document in the specified directory
        webpage.save_to_txt(directory=save_dir, filename=filename)

        # Append the URL to the processed URLs file
        append_processed_url(processed_file_path, url)

        logger.info(f"Added content from {url} to '{filename}'.")

    logger.info(f"All webpages have been processed and saved to '{save_dir.resolve()}'.")
    logger.info(f"Processed URLs have been recorded in '{processed_file_path.resolve()}'.")
    print(f"All webpages have been processed and saved in '{save_dir.resolve()}'.")
    print(f"Processed URLs have been recorded in '{processed_file_path.resolve()}'.")
    


# Example Usage
if __name__ == "__main__":
    # Define a list of URLs to parse
    urls_to_parse = [
        "https://www.wichita.edu/about/innovation_campus/",
        "https://www.wichita.edu/about/innovation_campus/partnerships.php",
        "https://www.wichita.edu/about/innovation_campus/",
        "https://www.wichita.edu/academics/centers_and_institutes.php",
        "https://www.wichita.edu/about/innovation_campus/partnerships.php",
        "https://www.wichita.edu/about/innovation_campus/facilities.php",
        "https://www.wichita.edu/about/innovation_campus/students.php",
        "https://www.wichita.edu/about/innovation_campus/history.php",
        "https://www.wichita.edu/about/about_wichita.php",
        "https://www.wichita.edu/about/innovation_campus/partnership-portal/index.php",
        "https://www.wichita.edu/about/innovation_campus/history.php",
        "https://www.wichita.edu/about/wsunews/news/2023/10-oct/aurp_emerging_park_3.php",
        "https://www.wichita.edu/about/wsunews/news/2024/11-nov/NSF_3.php",
        "https://www.wichita.edu/industry_and_defense/NIAR/",
        # Add more URLs as needed
    ]

    # Optional: Define a custom output directory
    # If not provided, documents will be saved in 'webpage_data' folder inside the project directory
    custom_output_directory = None  # e.g., "C:/Users/YourName/Documents/WebScrapes"

    # Optional: Define a custom processed URLs file
    # If not provided, 'processed_urls.txt' will be used in the project directory
    custom_processed_file = None  # e.g., "C:/Users/YourName/Documents/processed_urls.txt"

    # Process multiple webpages and save each to its own TXT file
    process_multiple_webpages(urls_to_parse, custom_output_directory, custom_processed_file)
