import httpx
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

r = httpx.get('https://www.rts.ch/info/', follow_redirects=True, headers=headers)
print('Homepage status:', r.status_code)
links = re.findall(r'href=["\']([^"\']+)["\']', r.text, re.I)
matches = [l for l in set(links) if any(k in l.lower() for k in ['rss', 'feed', 'xml', 'flux'])]
print('Matches:', matches)
