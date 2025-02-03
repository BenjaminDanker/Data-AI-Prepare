import re
import json
from typing import Optional
import requests
from bs4 import BeautifulSoup, Comment
import logging
from pathlib import Path
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
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
        self.images: list = []

        self._fetch_html()
        if self.html:
            self._parse_html()
            self._process_html()

    def _fetch_html(self) -> None:
        """Fetch the raw HTML content from the URL."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; WebScraper/1.0; +http://yourwebsite.com/bot)"}
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
        """Extract title, text, and images from the HTML."""
        if not self.soup:
            logger.warning("No BeautifulSoup object to process")
            return

        # Remove unnecessary tags
        unwanted_tags = ["script", "style", "form", "nav", "header", "aside"]
        for tag in self.soup.find_all(unwanted_tags):
            tag.decompose()
        logger.info(f"Removed tags: {unwanted_tags}")

        # Remove comments
        for comment in self.soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        logger.info("Removed comments from HTML")

        # Extract title
        if self.soup.title and self.soup.title.string:
            self.title = self.soup.title.string.strip()
            logger.info(f"Extracted title: {self.title}")
        else:
            logger.warning("No title found in the HTML")

        # Extract text content
        self.text = self._extract_text()
        logger.info("Extracted text from HTML")

        # Extract images
        self.images = self._extract_images()
        logger.info("Extracted image data")

    def _extract_text(self) -> str:
        """Extract clean text from the HTML, preserving newlines."""
        lines = []
        block_tags = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
        
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
        return final_text

    def _extract_images(self) -> list:
        """Extract image sources and alt texts."""
        images = []
        for img in self.soup.find_all("img"):
            src = img.get("src", "").strip()
            alt_text = img.get("alt", "").strip()
            images.append({"src": src, "alt_text": alt_text})
        return images

    def save_to_json(self, directory: Optional[Path] = None) -> None:
        """Save extracted data as a JSON file formatted for DataStax upload."""
        if directory is None:
            directory = Path.cwd() / "webpage_json"

        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

        filename = re.sub(r'[^a-zA-Z0-9_-]', '_', self.title or "untitled") + ".json"
        file_path = directory / filename

        data = {
            "dataset": "web_scraped_data",
            "documents": [
                {
                    "url": self.url,
                    "title": self.title,
                    "text": self.text,
                    "images": self.images
                }
            ]
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved JSON data to {file_path}")


def process_multiple_webpages(urls: list, output_directory: Optional[str] = None):
    """Process multiple URLs and save each webpage's content to a JSON file."""
    save_dir = Path(output_directory) if output_directory else Path.cwd() / "webpage_json"
    if not save_dir.exists():
        save_dir.mkdir(parents=True, exist_ok=True)

    for idx, url in enumerate(set(urls), start=1):
        logger.info(f"Processing {idx}/{len(urls)}: {url}")
        webpage = ParsedWebpage(url)

        if not webpage.title and not webpage.text:
            logger.warning(f"No content extracted from {url}. Skipping.")
            continue

        webpage.save_to_json(directory=save_dir)

    logger.info(f"All webpages processed and saved to '{save_dir.resolve()}'.")
    print(f"All webpages saved in '{save_dir.resolve()}'.")


# Example Usage
if __name__ == "__main__":
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
    process_multiple_webpages(urls_to_parse)
