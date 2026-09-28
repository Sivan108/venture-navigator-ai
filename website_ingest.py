from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


MAX_PAGE_CHARS = 7000
MAX_TOTAL_CHARS = 24000
MAX_PAGES = 5

PAGE_KEYWORDS = (
    "course",
    "courses",
    "training",
    "programme",
    "program",
    "services",
    "products",
    "solutions",
    "about",
    "what-we-do",
    "offering",
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139 Safari/537.36 "
        "VentureNavigatorAI/1.0"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-ZA,en;q=0.9",
    "Cache-Control": "no-cache",
}


BLOCK_TEXT = (
    "access denied",
    "checking your browser",
    "verify you are human",
    "captcha",
    "security check",
    "attention required",
    "temporarily blocked",
    "bot detection",
)


def _normalise_url(url: str) -> str:
    url = (url or "").strip()

    if not url:
        raise ValueError("No website URL supplied.")

    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url

    return url


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only public HTTP or HTTPS websites are supported.")

    hostname = parsed.hostname

    if not hostname:
        raise ValueError("The website address is invalid.")

    if hostname.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Local/internal addresses are not permitted.")

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(
            f"The website hostname could not be resolved: {hostname}"
        ) from exc

    for item in addresses:
        raw_ip = item[4][0]

        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(
                "The supplied address resolves to a private or restricted network."
            )


def _clean_html(html: str) -> tuple[str, BeautifulSoup]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "form",
            "nav",
            "footer",
        ]
    ):
        tag.decompose()

    text = soup.get_text("\n", strip=True)

    lines = []
    previous = None

    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        # Ignore WordPress/PHP diagnostic messages that may leak into
        # otherwise valid public page content.
        lower_line = line.lower()
        if (
            lower_line.startswith("warning:")
            or lower_line.startswith("notice:")
            or lower_line.startswith("deprecated:")
        ) and (
            "wp-content" in lower_line
            or "wp-includes" in lower_line
            or " on line " in lower_line
        ):
            continue

        if line == previous:
            continue

        previous = line
        lines.append(line)

    return "\n".join(lines), soup


def _looks_blocked(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in BLOCK_TEXT)


def _fetch(session: requests.Session, url: str) -> dict:
    _validate_public_url(url)

    response = session.get(
        url,
        headers=HEADERS,
        timeout=(8, 15),
        allow_redirects=True,
    )

    response.raise_for_status()

    final_url = response.url
    _validate_public_url(final_url)

    content_type = response.headers.get("content-type", "").lower()

    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise ValueError(
            f"The page did not return HTML content ({content_type or 'unknown type'})."
        )

    if len(response.content) > 3_000_000:
        raise ValueError("The page is too large to process safely.")

    text, soup = _clean_html(response.text)

    if len(text) < 80:
        raise ValueError("The website returned too little readable text.")

    if _looks_blocked(text[:2500]):
        raise ValueError(
            "The website appears to have returned a bot/security challenge rather "
            "than normal page content."
        )

    return {
        "url": final_url,
        "text": text[:MAX_PAGE_CHARS],
        "soup": soup,
    }


def _candidate_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    base_host = (urlparse(base_url).hostname or "").lower()

    scored = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()

        if not href:
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme not in ("http", "https"):
            continue

        host = (parsed.hostname or "").lower()

        if host != base_host:
            continue

        path = parsed.path.lower()
        label = anchor.get_text(" ", strip=True).lower()
        combined = f"{path} {label}"

        score = sum(1 for keyword in PAGE_KEYWORDS if keyword in combined)

        if score:
            clean = absolute.split("#", 1)[0]
            scored.append((score, clean))

    scored.sort(key=lambda item: item[0], reverse=True)

    unique = []
    seen = {base_url.split("#", 1)[0].rstrip("/")}

    for _, link in scored:
        key = link.rstrip("/")

        if key in seen:
            continue

        seen.add(key)
        unique.append(link)

        if len(unique) >= MAX_PAGES - 1:
            break

    return unique


def ingest_website(url: str) -> dict:
    """
    Read a public business website and a small number of useful internal pages.

    This does not bypass authentication, CAPTCHA, paywalls or explicit access
    controls. It only retrieves publicly available HTML.
    """

    try:
        start_url = _normalise_url(url)
        _validate_public_url(start_url)

        session = requests.Session()

        homepage = _fetch(session, start_url)

        pages = [
            {
                "url": homepage["url"],
                "text": homepage["text"],
            }
        ]

        links = _candidate_links(
            homepage["url"],
            homepage["soup"],
        )

        for link in links:
            if len(pages) >= MAX_PAGES:
                break

            try:
                page = _fetch(session, link)

                pages.append(
                    {
                        "url": page["url"],
                        "text": page["text"],
                    }
                )

            except Exception:
                # One blocked/broken internal page should not invalidate
                # useful content already retrieved from the website.
                continue

        parts = []

        for page in pages:
            parts.append(
                f"SOURCE PAGE: {page['url']}\n"
                f"{page['text']}"
            )

        context = "\n\n--- WEBSITE PAGE ---\n\n".join(parts)
        context = context[:MAX_TOTAL_CHARS]

        return {
            "ok": True,
            "context": context,
            "pages": [page["url"] for page in pages],
            "error": None,
        }

    except Exception as exc:
        return {
            "ok": False,
            "context": "",
            "pages": [],
            "error": str(exc),
        }
