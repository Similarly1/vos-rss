import httpx
import feedparser

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def robust_parse_feed(url: str):
    # 1. Try httpx fetch with browser User-Agent
    try:
        r = httpx.get(url, follow_redirects=True, headers=headers, timeout=12.0)
        if r.status_code == 200:
            parsed = feedparser.parse(r.content)
            if parsed.entries:
                return parsed
    except Exception as e:
        print(f"[httpx fetch failed for {url}]: {e}")

    # 2. Fallback directly to feedparser built-in HTTP fetcher
    parsed = feedparser.parse(url, agent=headers["User-Agent"])
    if parsed.entries:
        return parsed

    # 3. Fallback to trying url + /feed or /rss if not ending in feed/xml
    if not url.endswith('/feed') and not url.endswith('/rss') and not url.endswith('.xml'):
        for alt in [url.rstrip('/') + '/feed', url.rstrip('/') + '/rss']:
            try:
                r = httpx.get(alt, follow_redirects=True, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    parsed = feedparser.parse(r.content)
                    if parsed.entries:
                        return parsed
            except Exception:
                pass

    return parsed

# Test Le Temps
p1 = robust_parse_feed("https://www.letemps.ch/rss")
print("Le Temps (/rss -> /feed fallback): entries:", len(p1.entries), "title:", p1.feed.get("title"))

# Test Le Monde
p2 = robust_parse_feed("https://www.lemonde.fr/rss/une.xml")
print("Le Monde: entries:", len(p2.entries), "title:", p2.feed.get("title"))
