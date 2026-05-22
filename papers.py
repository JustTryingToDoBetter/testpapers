
from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, Tag


SOURCE_URL = "https://www.testpapers.co.za/gr11/mathematics-literature"
OUTPUT_DIR = Path("grade11_mathematical_literacy_papers")
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}


def safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\s().,\-]+", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "download.pdf"


def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    res = session.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def extract_drive_id(url: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "id" in qs:
        return qs["id"][0]

    patterns = [
        r"/folders/([^/?#]+)",
        r"/file/d/([^/?#]+)",
        r"/open\?id=([^&]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def is_google_drive_url(url: str) -> bool:
    return "drive.google.com" in url


def nearest_year(anchor: Tag) -> str:
    heading = anchor.find_previous(["h3", "h2"])
    if not heading:
        return "unknown"

    text = heading.get_text(" ", strip=True)
    match = re.search(r"\b(20\d{2})\b", text)
    return match.group(1) if match else "unknown"


def scrape_source_page(session: requests.Session) -> list[dict[str, str]]:
    soup = get_soup(session, SOURCE_URL)

    folders: list[dict[str, str]] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        href = urljoin(SOURCE_URL, a["href"])

        if not title:
            continue

        if not is_google_drive_url(href):
            continue

        if href in seen:
            continue

        seen.add(href)

        folders.append(
            {
                "year": nearest_year(a),
                "folder_title": title,
                "folder_url": href,
            }
        )

    return folders


def scrape_drive_folder(session: requests.Session, folder_url: str) -> list[dict[str, str]]:
    soup = get_soup(session, folder_url)

    files: list[dict[str, str]] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        file_title = a.get_text(" ", strip=True)
        file_url = urljoin(folder_url, a["href"])

        if not file_title.lower().endswith(".pdf"):
            continue

        file_id = extract_drive_id(file_url)

        if not file_id:
            continue

        if file_id in seen:
            continue

        seen.add(file_id)

        files.append(
            {
                "file_title": file_title,
                "file_url": file_url,
                "file_id": file_id,
            }
        )

    return files


def download_drive_file(
    session: requests.Session,
    file_id: str,
    destination: Path,
) -> None:
    url = "https://drive.google.com/uc"
    params = {"export": "download", "id": file_id}

    response = session.get(url, params=params, headers=HEADERS, stream=True, timeout=60)

    # Handles Google Drive's virus-scan confirmation page for some files.
    token = None
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            token = value
            break

    if token:
        params["confirm"] = token
        response = session.get(url, params=params, headers=HEADERS, stream=True, timeout=60)

    response.raise_for_status()

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 128):
            if chunk:
                f.write(chunk)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    rows: list[dict[str, str]] = []

    with requests.Session() as session:
        folders = scrape_source_page(session)

        for folder in folders:
            print(f"Scraping {folder['year']} - {folder['folder_title']}")

            try:
                files = scrape_drive_folder(session, folder["folder_url"])
            except requests.RequestException as e:
                print(f"  Failed folder: {e}")
                continue

            for file in files:
                year_dir = OUTPUT_DIR / folder["year"]
                filename = safe_filename(file["file_title"])
                destination = year_dir / filename

                row = {
                    "year": folder["year"],
                    "folder_title": folder["folder_title"],
                    "folder_url": folder["folder_url"],
                    "file_title": file["file_title"],
                    "file_url": file["file_url"],
                    "file_id": file["file_id"],
                    "local_path": str(destination),
                }

                rows.append(row)

                if destination.exists():
                    print(f"  Exists: {filename}")
                    continue

                try:
                    print(f"  Downloading: {filename}")
                    download_drive_file(session, file["file_id"], destination)
                    time.sleep(1)
                except requests.RequestException as e:
                    print(f"  Failed download: {filename} - {e}")

        with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "year",
                    "folder_title",
                    "folder_url",
                    "file_title",
                    "file_url",
                    "file_id",
                    "local_path",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

    print(f"\nDone. Downloaded/scraped {len(rows)} PDF entries.")
    print(f"Manifest saved to: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()