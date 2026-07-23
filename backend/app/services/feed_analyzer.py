import re
import httpx
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

def detect_language_from_text(text: str) -> str:
    """
    Simple & fast heuristic to detect language (fr, en, de, es) based on common words.
    """
    if not text:
        return "fr"
    
    t = text.lower()
    
    # German indicators
    de_words = [" und ", " der ", " die ", " das ", " mit ", " von ", " ist ", " auf ", " für "]
    de_score = sum(1 for w in de_words if w in t)
    
    # Spanish indicators
    es_words = [" y ", " el ", " la ", " los ", " las ", " con ", " por ", " para ", " en ", " del "]
    es_score = sum(1 for w in es_words if w in t)
    
    # English indicators
    en_words = [" and ", " the ", " to ", " of ", " in ", " with ", " for ", " on ", " is ", " that "]
    en_score = sum(1 for w in en_words if w in t)
    
    # French indicators
    fr_words = [" et ", " le ", " la ", " les ", " des ", " du ", " dans ", " pour ", " avec ", " une "]
    fr_score = sum(1 for w in fr_words if w in t)

    scores = {"de": de_score, "es": es_score, "en": en_score, "fr": fr_score}
    best_lang = max(scores, key=scores.get)
    if scores[best_lang] > 1:
        return best_lang

    return "fr"

def analyze_feed_completeness(feed_url: str) -> dict:
    """
    Analyzes an RSS feed to check average article content length and detect language.
    Returns {"is_full_text": bool, "avg_char_length": int, "language": str}
    """
    if not HAS_FEEDPARSER:
        return {"is_full_text": True, "avg_char_length": 1000, "language": "fr"}

    try:
        res = httpx.get(feed_url, follow_redirects=True, timeout=10.0, headers={"User-Agent": "Vos-RSS-Analyzer/1.0"})
        fp = feedparser.parse(res.content)
        
        if not fp.entries:
            return {"is_full_text": False, "avg_char_length": 0, "language": "fr"}

        total_length = 0
        all_text = ""
        sample_entries = fp.entries[:5]

        for entry in sample_entries:
            content = entry.get("summary") or entry.get("description") or ""
            if "content" in entry and len(entry.content) > 0:
                content = entry.content[0].get("value", content)
            
            clean = re.sub(r'<[^>]+>', ' ', content).strip()
            total_length += len(clean)
            all_text += " " + clean

        avg_length = total_length // len(sample_entries)
        detected_lang = detect_language_from_text(all_text)
        
        # Consider a feed full_text natively if average length > 450 characters
        is_full = avg_length >= 450

        return {
            "is_full_text": is_full,
            "avg_char_length": avg_length,
            "language": detected_lang
        }
    except Exception as e:
        print(f"[Feed Analyzer Note] Impossible d'analyser {feed_url}: {e}")
        return {"is_full_text": True, "avg_char_length": 800, "language": "fr"}
