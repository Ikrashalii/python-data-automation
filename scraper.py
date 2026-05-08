import csv
from typing import List, Dict

import requests
from bs4 import BeautifulSoup


URL = "https://books.toscrape.com/"
CSV_FILE = "scraped_books.csv"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_page(url: str) -> str:
    """Fetch page content with basic error handling."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not reach '{url}': {exc}") from exc


def parse_books(html: str) -> List[Dict[str, str]]:
    """Parse first-page book data: title, price, and availability."""
    soup = BeautifulSoup(html, "html.parser")
    books = []

    for article in soup.select("article.product_pod"):
        title_tag = article.select_one("h3 a")
        price_tag = article.select_one("p.price_color")
        availability_tag = article.select_one("p.instock.availability")

        title = title_tag.get("title", "").strip() if title_tag else ""
        price = price_tag.get_text(strip=True) if price_tag else ""
        availability = (
            availability_tag.get_text(strip=True) if availability_tag else ""
        )

        books.append(
            {
                "Title": title,
                "Price": price,
                "Availability": availability,
            }
        )

    return books


def save_to_csv(rows: List[Dict[str, str]], filename: str) -> None:
    """Save scraped data to CSV file."""
    with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["Title", "Price", "Availability"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    try:
        html = fetch_page(URL)
    except RuntimeError as err:
        print(err)
        return

    books = parse_books(html)
    save_to_csv(books, CSV_FILE)
    print(f"Scraped {len(books)} books and saved to '{CSV_FILE}'.")


if __name__ == "__main__":
    main()
