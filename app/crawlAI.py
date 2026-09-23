import sys
import os
import io
import re
import json
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set, Union, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR.parent / "source_repository.json"
EXTRACTIONS_DIR = BASE_DIR / "extracted_content"


def load_repository_config(config_path: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Load the repository JSON configuration file."""
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_source_config_by_id(source_id: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve a specific source configuration by its source_id."""
    data = load_repository_config(config_path)
    if isinstance(data, list):
        for item in data:
            if item.get("source_id") == source_id:
                return item
        raise ValueError(f"Source with id '{source_id}' not found in configuration.")
    elif isinstance(data, dict):
        if data.get("source_id") == source_id:
            return data
        raise ValueError(f"Source with id '{source_id}' not found in configuration.")
    raise ValueError("Invalid configuration format.")


def calculate_content_hash(text: str, algorithm: str = "sha256") -> Optional[str]:
    """Calculate hash of the scraped content for change detection."""
    if not text:
        return None
    h = getattr(hashlib, algorithm.lower(), hashlib.sha256)()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def is_allowed_url(url: str, allowed_domains: List[str]) -> bool:
    """Check if URL host matches any in the allowed_domains list."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().split(":")[0]
        if not netloc:
            return False
        return any(netloc == domain.lower() or netloc.endswith("." + domain.lower()) for domain in allowed_domains)
    except Exception:
        return False


def is_binary_download_url(url: str) -> bool:
    """Filter out binary downloadable files that cause Playwright navigation crashes."""
    path_lower = urlparse(url).path.lower()
    return path_lower.endswith((".doc", ".docx", ".zip", ".tar", ".gz", ".exe", ".xlsx", ".xls", ".csv", ".mp3", ".mp4"))


def sanitize_filename(name: str, max_length: int = 60) -> str:
    """Create a safe filename from URL or title."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name)
    cleaned = re.sub(r'\s+', "_", cleaned)
    cleaned = cleaned.strip("._")
    return cleaned[:max_length] if cleaned else "document"


def save_extracted_content_to_files(crawl_result: Dict[str, Any], source_id: str) -> str:
    """
    Saves extracted HTML/PDF content and metadata into files under app/extracted_content/<source_id>/.
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = EXTRACTIONS_DIR / sanitize_filename(source_id) / timestamp_str
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save summary & metadata JSON
    summary_path = target_dir / "crawl_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_id": source_id,
            "seed_url": crawl_result.get("seed_url"),
            "total_documents_scraped": crawl_result.get("total_documents_scraped"),
            "total_html_pages": crawl_result.get("total_html_pages"),
            "total_pdfs_parsed": crawl_result.get("total_pdfs_parsed"),
            "combined_content_hash": crawl_result.get("combined_content_hash"),
            "metadata": crawl_result.get("metadata")
        }, f, indent=2)

    # 2. Save each document to a markdown file
    docs = crawl_result.get("documents", [])
    for idx, doc in enumerate(docs, start=1):
        doc_type = doc.get("type", "doc")
        url_part = sanitize_filename(doc.get("url", "").split("//")[-1].replace("/", "_"))
        filename = f"{idx:03d}_{doc_type}_{url_part}.md"
        doc_file_path = target_dir / filename

        with open(doc_file_path, "w", encoding="utf-8") as f:
            f.write(f"# URL: {doc.get('url')}\n")
            f.write(f"- **Type**: {doc_type.upper()}\n")
            f.write(f"- **Content Hash (SHA-256)**: {doc.get('content_hash')}\n")
            if doc_type == "pdf":
                f.write(f"- **Page Count**: {doc.get('page_count', 0)}\n")
            f.write("\n---\n\n")
            f.write(doc.get("content") or "No content extracted.")

    return str(target_dir)


def extract_center_links(html: str, base_url: str, allowed_domains: List[str]) -> Tuple[Set[str], Set[str]]:
    """
    Extract links and PDFs specifically from the main/center content body,
    ignoring site navigation bars, menus, headers, and footers.
    """
    discovered_html: Set[str] = set()
    discovered_pdf: Set[str] = set()

    if not html:
        return discovered_html, discovered_pdf

    soup = BeautifulSoup(html, "html.parser")

    content_root = (
        soup.find(id="content") or
        soup.find(id="main-content") or
        soup.find(id="pagebody") or
        soup.find("main") or
        soup.find("article") or
        soup.find("body") or
        soup
    )

    for tag in content_root.find_all(["nav", "header", "footer"]):
        tag.decompose()
    for tag in content_root.find_all(id=["header", "mainnav", "footer", "sidebar", "menu", "sidemenu", "breadcrumbs"]):
        tag.decompose()
    for tag in content_root.find_all(class_=["header", "nav", "navbar", "footer", "sidebar", "menu", "breadcrumbs", "nodisplay"]):
        tag.decompose()

    for a_tag in content_root.find_all("a", href=True):
        href = a_tag["href"].strip()
        abs_url = urljoin(base_url, href).split("#")[0]

        if not abs_url.startswith(("http://", "https://")):
            continue
        if allowed_domains and not is_allowed_url(abs_url, allowed_domains):
            continue
        if is_binary_download_url(abs_url):
            continue

        if abs_url.lower().endswith(".pdf"):
            discovered_pdf.add(abs_url)
        elif abs_url != base_url:
            discovered_html.add(abs_url)

    return discovered_html, discovered_pdf


async def download_and_extract_pdf(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Download PDF and extract text content using pypdf."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {
                    "url": url,
                    "type": "pdf",
                    "success": False,
                    "error": f"HTTP status {resp.status_code}",
                    "text": None,
                    "content_hash": None,
                    "page_count": 0
                }

            pdf_file = io.BytesIO(resp.content)
            reader = PdfReader(pdf_file)
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(f"--- Page {i+1} ---\n{page_text}")

            full_text = "\n\n".join(extracted_pages)
            return {
                "url": url,
                "type": "pdf",
                "success": True,
                "error": None,
                "text": full_text,
                "content_hash": calculate_content_hash(full_text),
                "page_count": len(reader.pages)
            }
    except Exception as e:
        return {
            "url": url,
            "type": "pdf",
            "success": False,
            "error": str(e),
            "text": None,
            "content_hash": None,
            "page_count": 0
        }


async def _crawl_internal(
    config_data: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    if config_data:
        metadata = config_data
    elif source_id:
        metadata = get_source_config_by_id(source_id)
    else:
        configs = load_repository_config()
        metadata = configs[0] if isinstance(configs, list) else configs
    
    current_source_id = metadata.get("source_id", "default_source")
    source_info = metadata.get("source", {})
    crawl_settings = metadata.get("crawl", {})
    monitoring = metadata.get("monitoring", {})
    hash_algorithm = monitoring.get("hash_algorithm", "sha256")
    allowed_domains = source_info.get("allowed_domains", [])
    
    max_depth = int(crawl_settings.get("max_depth", 1))
    follow_links = bool(crawl_settings.get("follow_links", True))
    include_pdf = bool(crawl_settings.get("include_pdf", True))
    request_timeout = int(crawl_settings.get("request_timeout_seconds", 30))

    seed_urls: List[str] = source_info.get("seed_urls", [])
    target_url = seed_urls[0] if seed_urls else source_info.get("base_url")

    if not target_url:
        raise ValueError("No target or seed URL specified in configuration.")

    crawled_at = datetime.now(timezone.utc).isoformat()

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "header", "footer", "script", "style", "aside"],
        excluded_selector="#header, #mainnav, #footer, #sidebar, #menu, #sidemenu, #breadcrumbs, .nodisplay"
    )

    scraped_documents: List[Dict[str, Any]] = []
    visited_urls: Set[str] = set()
    discovered_pdf_urls: Set[str] = set()

    queue: List[Tuple[str, int]] = [(target_url, 1)]

    async with AsyncWebCrawler() as crawler:
        while queue:
            current_url, current_depth = queue.pop(0)

            if current_url in visited_urls:
                continue

            visited_urls.add(current_url)

            try:
                result = await crawler.arun(url=current_url, config=crawl_config)
                if not result.success:
                    if current_url == target_url:
                        return {
                            "success": False,
                            "url": target_url,
                            "markdown": None,
                            "error": result.error_message,
                            "metadata": metadata
                        }
                    continue

                doc_hash = calculate_content_hash(result.markdown or "", hash_algorithm)
                scraped_documents.append({
                    "url": current_url,
                    "depth": current_depth,
                    "type": "html",
                    "title": "Seed Page" if current_depth == 1 else f"Depth {current_depth} Page",
                    "content": result.markdown,
                    "content_hash": doc_hash
                })

                if result.html:
                    html_links, pdf_links = extract_center_links(result.html, current_url, allowed_domains)
                    discovered_pdf_urls.update(pdf_links)

                    if follow_links and (current_depth < max_depth):
                        for sub_url in html_links:
                            if sub_url not in visited_urls:
                                queue.append((sub_url, current_depth + 1))

            except Exception as e:
                if current_url == target_url:
                    return {
                        "success": False,
                        "url": target_url,
                        "markdown": None,
                        "error": str(e),
                        "metadata": metadata
                    }
                continue

    # Download and parse discovered PDFs
    if include_pdf and discovered_pdf_urls:
        pdf_tasks = [download_and_extract_pdf(pdf_url, timeout=request_timeout) for pdf_url in list(discovered_pdf_urls)[:10]]
        pdf_results = await asyncio.gather(*pdf_tasks)
        for pdf_res in pdf_results:
            if pdf_res["success"] and pdf_res["text"]:
                scraped_documents.append({
                    "url": pdf_res["url"],
                    "depth": 1,
                    "type": "pdf",
                    "page_count": pdf_res["page_count"],
                    "content": pdf_res["text"],
                    "content_hash": pdf_res["content_hash"]
                })

    all_content_str = "\n\n".join([doc.get("content", "") for doc in scraped_documents if doc.get("content")])
    combined_hash = calculate_content_hash(all_content_str, hash_algorithm)

    response_data = {
        "success": True,
        "seed_url": target_url,
        "max_depth_applied": max_depth,
        "total_documents_scraped": len(scraped_documents),
        "total_html_pages": sum(1 for d in scraped_documents if d["type"] == "html"),
        "total_pdfs_parsed": sum(1 for d in scraped_documents if d["type"] == "pdf"),
        "discovered_pdf_urls": list(discovered_pdf_urls),
        "documents": scraped_documents,
        "combined_content_hash": combined_hash,
        "metadata": {
            "source_id": metadata.get("source_id"),
            "jurisdiction": metadata.get("jurisdiction"),
            "source": source_info,
            "crawl_settings": crawl_settings,
            "monitoring": monitoring,
            "status": metadata.get("status"),
            "timestamps": {
                "created_at": metadata.get("timestamps", {}).get("created_at"),
                "updated_at": metadata.get("timestamps", {}).get("updated_at"),
                "last_crawled_at": crawled_at,
                "last_success_at": crawled_at
            }
        }
    }

    # Save files to disk in app/extracted_content/<source_id>/<timestamp>/
    saved_folder = save_extracted_content_to_files(response_data, current_source_id)
    response_data["saved_directory"] = saved_folder

    return response_data


def _run_in_isolated_thread(
    config_data: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(_crawl_internal(config_data=config_data, source_id=source_id))


async def crawl_url(
    config_data: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crawls URL respecting max_depth, isolates center links, extracts PDFs, and saves output to disk.
    """
    return await asyncio.to_thread(_run_in_isolated_thread, config_data, source_id)


async def main():
    print("Running crawl and storing extracted content to files...")
    res = await crawl_url(source_id="us-sc-code-title44-ch115")
    if res["success"]:
        print("\n=== CRAWL SUMMARY ===")
        print(f"Source ID: {res['metadata']['source_id']}")
        print(f"Total documents: {res['total_documents_scraped']}")
        print(f"Saved directory: {res['saved_directory']}")
    else:
        print(f"Failed to fetch content: {res['error']}")


if __name__ == "__main__":
    asyncio.run(main())