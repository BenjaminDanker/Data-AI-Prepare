"""
Parse out text (and more) from multiple HTML files,
leveraging unstructured for improved parsing,
then save the extracted text to a .txt file.
"""
import re
from typing import Optional
import requests
from bs4 import BeautifulSoup, Comment
import logging
from pathlib import Path
from urllib.parse import urlparse
import os

# ------------ Attempt to import unstructured ------------
try:
    from unstructured.partition.html import partition_html
except ImportError:
    partition_html = None
    # You can log or print a warning here if desired.

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Log only to console
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
        """
        Clean and extract desired content from the HTML.
        Try unstructured first. If that fails, fall back to BeautifulSoup.
        """
        if not self.soup:
            logger.warning("No BeautifulSoup object to process")
            return

        # 1. Try unstructured if available
        if partition_html is not None:
            try:
                elements = partition_html(text=self.html)
                unstructured_text = "\n".join(str(el) for el in elements).strip()
                if unstructured_text:
                    self.text = unstructured_text
                    self._extract_title_from_unstructured(elements)
                    logger.info("Successfully parsed HTML with unstructured.")
                    return
            except Exception as e:
                logger.warning(f"Failed to parse with unstructured: {e}. Falling back to BeautifulSoup.")

        # 2. Fallback: remove unwanted tags, comments, etc. with BeautifulSoup
        unwanted_tags = ["script", "style", "form", "nav", "header", "aside"]
        for tag in self.soup.find_all(unwanted_tags):
            tag.decompose()
        logger.info(f"Removed tags: {unwanted_tags}")

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

    def _extract_title_from_unstructured(self, elements):
        """
        Very basic approach to guess a title from unstructured elements.
        You can customize this for your own needs.
        """
        for el in elements:
            if "<title>" in str(el).lower():
                self.title = str(el).strip()
                logger.info(f"Unstructured-based title: {self.title}")
                break

    def _replace_images(self) -> None:
        """Replace <img> tags with descriptive alt text."""
        for img in self.soup.find_all("img"):
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
        """
        Extract and clean visible text from the HTML, preserving newlines,
        and removing '©' symbols.
        """
        lines = []
        block_tags = {
            "p", "div", "section", "article", "header", "footer",
            "nav", "aside", "h1", "h2", "h3", "h4", "h5", "h6", "li"
        }

        for element in self.soup.descendants:
            if getattr(element, 'name', None) in block_tags:
                lines.append("\n")
            if isinstance(element, str):
                text = ' '.join(element.split())
                if text:
                    lines.append(text + " ")

        raw_text = ''.join(lines)
        cleaned_text = re.sub(r'\n+', '\n', raw_text)
        cleaned_lines = [line.strip() for line in cleaned_text.split('\n')]
        final_text = '\n'.join([line for line in cleaned_lines if line])
        final_text = re.sub(r'©\s*\d{0,4}', '', final_text)
        return final_text

    # ------------ New Method: Save Content to TXT file ------------
    def save_to_txt(self, directory: Optional[Path] = None, filename: Optional[str] = None) -> None:
        """
        Save the extracted text to a TXT file in the specified directory,
        using UTF-8 encoding and skipping any characters that can't be encoded.
        """
        # Determine the save directory
        if directory is None:
            project_dir = Path.cwd()
            directory = project_dir / "webpage_data"
        else:
            directory = Path(directory)

        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                return

        # Set default TXT filename if not provided
        if not filename:
            if self.title:
                sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", self.title)
                filename = f"{sanitized_title}.txt"
            else:
                parsed_url = urlparse(self.url)
                path = parsed_url.path.strip("/").replace("/", "_")
                if path:
                    filename = f"{parsed_url.netloc}_{path}.txt"
                else:
                    filename = f"{parsed_url.netloc}.txt"

        file_path = directory / filename

        # Build content: title (if available), URL, and text
        content_list = []
        if self.title:
            content_list.append(self.title)
        content_list.append(self.url)
        content_list.append(self.text)
        content = "\n\n".join(content_list)

        # Save to .txt with UTF-8 encoding, skipping unencodable characters
        try:
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            logger.info(f"TXT file saved successfully at {file_path}")
        except Exception as e:
            logger.error(f"Failed to save TXT at {file_path}: {e}")


def read_processed_urls(file_path: Path) -> set:
    """
    Read the processed URLs from a file and return them as a set.
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
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
        logger.info(f"Appended URL to {file_path}: {url}")
    except Exception as e:
        logger.error(f"Failed to append URL to {file_path}: {e}")


def process_multiple_webpages(urls: list, output_directory: Optional[str] = None, processed_file: Optional[str] = None) -> None:
    """
    Process multiple URLs and save each extracted content into its own .txt file.
    Skips URLs that have already been processed as per the 'processed_urls.txt' file.
    """
    if output_directory:
        save_dir = Path(output_directory)
    else:
        save_dir = Path.cwd() / "webpage_datatxt"

    if processed_file:
        processed_file_path = Path(processed_file)
    else:
        processed_file_path = Path.cwd() / "processed_urls.txt"

    processed_urls = read_processed_urls(processed_file_path)

    if not save_dir.exists():
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {save_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory {save_dir}: {e}")
            return

    unique_urls = list(set(urls))
    logger.info(f"Total unique URLs to process: {len(unique_urls)}")

    for idx, url in enumerate(unique_urls, start=1):
        if url in processed_urls:
            logger.info(f"URL already processed and skipped ({idx}/{len(unique_urls)}): {url}")
            continue

        logger.info(f"Processing URL {idx}/{len(unique_urls)}: {url}")
        webpage = ParsedWebpage(url)

        if not webpage.title and not webpage.text:
            logger.warning(f"No content extracted from {url}. Skipping.")
            continue

        # Build a text filename
        if webpage.title:
            sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", webpage.title)
            txt_filename = f"{sanitized_title}.txt"
        else:
            parsed_url = urlparse(webpage.url)
            path = parsed_url.path.strip("/").replace("/", "_")
            if path:
                txt_filename = f"{parsed_url.netloc}_{path}.txt"
            else:
                txt_filename = f"{parsed_url.netloc}.txt"

        # Save to TXT
        webpage.save_to_txt(directory=save_dir, filename=txt_filename)
        append_processed_url(processed_file_path, url)
        logger.info(f"Added content from {url} to '{txt_filename}'.")

    logger.info(f"All webpages have been processed and saved to '{save_dir.resolve()}'.")
    logger.info(f"Processed URLs have been recorded in '{processed_file_path.resolve()}'.")
    print(f"All webpages have been processed and saved in '{save_dir.resolve()}'.")
    print(f"Processed URLs have been recorded in '{processed_file_path.resolve()}'.")



# Example Usage
if __name__ == "__main__":
    # Define a list of URLs to parse
    urls_to_parse = [
        '''
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
        '''
        "https://www.wichita.edu/about/wsunews/news/2019/03-march/airbus_student_seat_design.php",
        "https://www.hyatt.com/hyatt-place/en-US/ictzw-hyatt-place-at-wichita-state-university",
        "https://www.wichita.edu/about/wsunews/news/2019/03-march/airbus_student_seat_design.php",
        "https://imdatacenters.com/",
        "https://www.airbus.com/en/about-us",
        "https://www.airbus.com/en",
        "https://www.atf.gov/",
        "https://www.bcg.com/about/overview",
        "https://connectednation.org/about",
        "https://www.3ds.com/about/company/what-is-dassault-systemes",
        "https://www2.deloitte.com/us/en/pages/about-deloitte/articles/about-deloitte.html",
        "https://hexagon.com/company/divisions/manufacturing-intelligence/what-we-do",
        "https://www.hyatt.com/hyatt-place/en-US",
        "https://imdatacenters.com/about/",
        "https://www.pacmartech.com/about",
        "https://www.netapp.com/company/",
        "https://www.spiritaero.com/company/overview/overview/",
        "https://www.spiritaero.com/company/programs/",
        "https://www.spiritaero.com/company/global-locations-contacts/",
        "https://www.spiritaero.com/company/community/overview/",
        "https://www.spiritaero.com/company/ethics-compliance/ethics-overview/",
        "https://txtav.com/en/careers/our-powerful-brands",
        "https://txtav.com/en/company/visitor-guide",
        "https://www.wichita.gov/1343/Academy",
        "https://ymcawichita.org/sites/default/files/2020-01/GWYMCA_Steve_Clark_YMCA_and_Student_Wellness_Center_Fact_Sheet_011720.pdf",
        "https://www.wichita.edu/about/public_information/wsu_topics/topics_ymca_wellness_center.php",
        "https://www.wichita.edu/about/wsunews/news/2024/01-jan/WBCrenderings_2.php",
        "https://www.wichita.edu/about/wsunews/news/2024/02-feb/AIsafety_3.php",
        # Add more URLs as needed
    ]

    # Optional: Define a custom output directory
    custom_output_directory = None

    # Optional: Define a custom processed URLs file
    custom_processed_file = None

    # Process multiple webpages and save each to its own TXT file
    process_multiple_webpages(urls_to_parse, custom_output_directory, custom_processed_file)
