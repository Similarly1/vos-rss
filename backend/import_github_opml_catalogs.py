"""
Script: import_github_opml_catalogs.py
Downloads OPML files from curated GitHub repositories (plenaryapp/awesome-rss-feeds)
and adds all feeds to the local catalog database.

Run from backend/ directory: python import_github_opml_catalogs.py
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse, quote

sys.path.insert(0, str(Path(__file__).parent))

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from app.services.catalog import add_or_update_catalog_feed, normalize_category

BASE_COUNTRY = "https://raw.githubusercontent.com/plenaryapp/awesome-rss-feeds/master/countries"
BASE_RECO = "https://raw.githubusercontent.com/plenaryapp/awesome-rss-feeds/master/recommended"

OPML_SOURCES = [
    # ── France (avec catégories pour meilleure classification) ──
    {
        "url": f"{BASE_COUNTRY}/with_category/France.opml",
        "fallback": f"{BASE_COUNTRY}/without_category/France.opml",
        "default_category": "Actualités & Presse",
        "language": "fr",
        "country": "FR",
        "tags": ["France", "Actualités"],
    },
    # ── Suisse ──
    {
        "url": f"{BASE_COUNTRY}/with_category/Switzerland.opml",
        "fallback": f"{BASE_COUNTRY}/without_category/Switzerland.opml",
        "default_category": "Suisse & Régional",
        "language": "fr",
        "country": "CH",
        "tags": ["Suisse", "Régional"],
    },
    # ── Allemagne (perspective européenne) ──
    {
        "url": f"{BASE_COUNTRY}/with_category/Germany.opml",
        "fallback": f"{BASE_COUNTRY}/without_category/Germany.opml",
        "default_category": "International & Monde",
        "language": "de",
        "country": "DE",
        "tags": ["Allemagne", "Europe"],
    },
    # ── UK ──
    {
        "url": f"{BASE_COUNTRY}/with_category/United Kingdom.opml",
        "fallback": f"{BASE_COUNTRY}/without_category/United Kingdom.opml",
        "default_category": "International & Monde",
        "language": "en",
        "country": "GB",
        "tags": ["Royaume-Uni", "International"],
    },
    # ── USA ──
    {
        "url": f"{BASE_COUNTRY}/with_category/United States.opml",
        "fallback": f"{BASE_COUNTRY}/without_category/United States.opml",
        "default_category": "International & Monde",
        "language": "en",
        "country": "US",
        "tags": ["Etats-Unis", "International"],
    },
    # ── Thématiques recommandées ──
    {
        "url": f"{BASE_RECO}/with_category/Business & Economy.opml",
        "fallback": f"{BASE_RECO}/without_category/Business & Economy.opml",
        "default_category": "Économie & Business",
        "language": "en",
        "country": "",
        "tags": ["Économie", "Business", "International"],
    },
    {
        "url": f"{BASE_RECO}/with_category/Science.opml",
        "fallback": f"{BASE_RECO}/without_category/Science.opml",
        "default_category": "Science & Climat",
        "language": "en",
        "country": "",
        "tags": ["Science", "International"],
    },
    {
        "url": f"{BASE_RECO}/with_category/Technology.opml",
        "fallback": f"{BASE_RECO}/without_category/Technology.opml",
        "default_category": "Technologie & Cyber",
        "language": "en",
        "country": "",
        "tags": ["Technologie", "International"],
    },
    {
        "url": f"{BASE_RECO}/with_category/Books.opml",
        "fallback": f"{BASE_RECO}/without_category/Books.opml",
        "default_category": "Culture & Société",
        "language": "en",
        "country": "",
        "tags": ["Culture", "Livres", "International"],
    },
]


def fetch_url(url: str) -> str | None:
    try:
        if HAS_HTTPX:
            r = httpx.get(url, follow_redirects=True, timeout=20.0,
                          headers={"User-Agent": "VOS-RSS-Importer/1.0"})
            if r.status_code == 200:
                return r.text
            print(f"    HTTP {r.status_code} for {url}")
        else:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "VOS-RSS-Importer/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    [WARN] {url}: {e}")
    return None


def sanitize_xml(text: str) -> str:
    """Remove characters that are illegal in XML 1.0 (including stray emoji in attributes)."""
    import re
    # Remove invalid XML 1.0 chars (control chars except \t \n \r)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Encode emoji/supplementary unicode in attribute values as XML entities or remove
    # Strategy: escape raw & in attributes not already escaped
    # Actually, the repo OPML files contain emoji inside text/title attributes.
    # ET.fromstring handles valid Unicode fine; the issue is unescaped & or < in URLs.
    # Let's fix bare & that aren't already &amp;
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', text)
    return text


def parse_opml(xml_text: str) -> list:
    feeds = []
    for attempt in [xml_text, sanitize_xml(xml_text)]:
        try:
            root = ET.fromstring(attempt)
            # Use deep search to find ALL outline elements at any depth
            for outline in root.findall(".//outline"):
                xml_url = (outline.attrib.get("xmlUrl")
                           or outline.attrib.get("url")
                           or outline.attrib.get("xmlurl") or "").strip()
                title = (outline.attrib.get("text")
                         or outline.attrib.get("title") or "").strip()
                html_url = (outline.attrib.get("htmlUrl")
                            or outline.attrib.get("htmlurl") or "").strip()
                if xml_url and xml_url.startswith("http"):
                    feeds.append({
                        "url": xml_url,
                        "title": title,
                        "site_url": html_url,
                    })
            return feeds
        except ET.ParseError:
            if attempt is xml_text:
                continue
            print(f"    [WARN] OPML could not be parsed even after sanitization")
    return feeds


def _extract_outlines(parent_el, feeds: list, parent_category):
    """Recursively extract feed outlines. Handles opml/body/folder/feed nesting."""
    for outline in parent_el.findall("outline"):
        xml_url = (outline.attrib.get("xmlUrl")
                   or outline.attrib.get("url")
                   or outline.attrib.get("xmlurl") or "").strip()
        title = (outline.attrib.get("text")
                 or outline.attrib.get("title") or "").strip()
        html_url = (outline.attrib.get("htmlUrl")
                    or outline.attrib.get("htmlurl") or "").strip()

        if xml_url and xml_url.startswith("http"):
            feeds.append({
                "url": xml_url,
                "title": title,
                "site_url": html_url,
                "folder": parent_category or "",
            })
        # Always recurse to find nested feeds (folders contain feeds)
        _extract_outlines(outline, feeds, parent_category=title or parent_category)


def import_source(source: dict) -> int:
    primary = source["url"]
    fallback = source.get("fallback")

    # URL-encode spaces in the path
    def encode_url(u):
        parts = u.split("/")
        return "/".join(quote(p, safe="") if i > 4 else p for i, p in enumerate(parts))

    print(f"\n  Fetching: {primary}")
    xml_text = fetch_url(encode_url(primary))

    if not xml_text and fallback:
        print(f"  Trying fallback: {fallback}")
        xml_text = fetch_url(encode_url(fallback))

    if not xml_text:
        print(f"  [SKIP] Could not fetch — skipping source")
        return 0

    feeds = parse_opml(xml_text)
    print(f"  Parsed {len(feeds)} feeds")

    added = 0
    for f in feeds:
        if not f["url"]:
            continue

        folder = f.get("folder", "")
        if folder:
            cat = normalize_category(folder)
            if cat == "Général" and source["default_category"] != "Général":
                cat = source["default_category"]
        else:
            cat = source["default_category"]

        feed_data = {
            "url": f["url"],
            "site_url": f.get("site_url", ""),
            "title": f.get("title", "") or f["url"],
            "description": "",
            "icon_url": "",
            "category": cat,
            "language": source["language"],
            "country": source["country"],
            "is_full_text": False,
            "is_verified": True,
        }

        try:
            feed_id = add_or_update_catalog_feed(feed_data, tags=source.get("tags", []))
            if feed_id:
                added += 1
        except Exception as e:
            print(f"    [ERR] {f['url']}: {e}")

    return added


def main():
    total = 0
    for source in OPML_SOURCES:
        n = import_source(source)
        print(f"  => {n} feeds upserted")
        total += n
    print(f"\nTotal: {total} feeds added/updated in catalog.")


if __name__ == "__main__":
    main()
