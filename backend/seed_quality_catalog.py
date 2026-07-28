"""
Script: seed_quality_catalog.py
Adds curated high-quality French and international RSS feeds to the catalog.
Run from backend/ directory: python seed_quality_catalog.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.catalog import add_or_update_catalog_feed

FEEDS = [
    # ── Audiovisuel public & Agences (Factuel, gratuit) ──
    {
        "url": "https://www.francetvinfo.fr/titres.rss",
        "site_url": "https://www.francetvinfo.fr",
        "title": "France Info – Titres",
        "description": "Les titres de l'actualité en continu de Franceinfo, audiovisuel public français.",
        "icon_url": "https://www.google.com/s2/favicons?domain=francetvinfo.fr&sz=128",
        "category": "Actualités & Presse",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": True,
        "factuality_rating": "Very High",
        "bias_rating": "Center",
        "media_type": "Agence",
        "tags": ["France", "Actualités", "Radio", "Télévision", "Public"],
    },
    {
        "url": "https://www.france24.com/fr/rss",
        "site_url": "https://www.france24.com/fr",
        "title": "France 24 – International",
        "description": "Toute l'actualité internationale en français sur France 24.",
        "icon_url": "https://www.google.com/s2/favicons?domain=france24.com&sz=128",
        "category": "International & Monde",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": True,
        "factuality_rating": "High",
        "bias_rating": "Center",
        "media_type": "Télévision",
        "tags": ["International", "France", "Télévision", "Public"],
    },
    {
        "url": "https://www.rfi.fr/fr/general/rss",
        "site_url": "https://www.rfi.fr/fr",
        "title": "RFI – Actualité internationale & Afrique",
        "description": "Radio France Internationale. Actualité mondiale et africaine en langue française.",
        "icon_url": "https://www.google.com/s2/favicons?domain=rfi.fr&sz=128",
        "category": "International & Monde",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": True,
        "factuality_rating": "High",
        "bias_rating": "Center",
        "media_type": "Radio",
        "tags": ["International", "Afrique", "Radio", "Public", "France"],
    },
    {
        "url": "https://feeds.euronews.com/feeds/fr/home.rss",
        "site_url": "https://fr.euronews.com",
        "title": "Euronews – Actualité européenne et internationale",
        "description": "Chaîne d'information européenne multilingue. Actualité internationale avec une perspective européenne.",
        "icon_url": "https://www.google.com/s2/favicons?domain=euronews.com&sz=128",
        "category": "International & Monde",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": True,
        "factuality_rating": "High",
        "bias_rating": "Center",
        "media_type": "Télévision",
        "tags": ["Europe", "International", "Télévision", "Multilingue"],
    },
    {
        "url": "https://rss.dw.com/xml/rss-fr-all",
        "site_url": "https://www.dw.com/fr",
        "title": "Deutsche Welle – Actualité en français",
        "description": "Deutsche Welle, media international allemand. Perspective européenne sur l'actualité mondiale.",
        "icon_url": "https://www.google.com/s2/favicons?domain=dw.com&sz=128",
        "category": "International & Monde",
        "language": "fr",
        "country": "DE",
        "is_verified": True,
        "is_jti_certified": True,
        "factuality_rating": "Very High",
        "bias_rating": "Center",
        "media_type": "Télévision",
        "tags": ["Europe", "International", "Allemagne", "Public"],
    },
    # ── Presse indépendante & Analyse ──
    {
        "url": "https://theconversation.com/fr/articles.atom",
        "site_url": "https://theconversation.com/fr",
        "title": "The Conversation – France",
        "description": "Articles de vulgarisation rédigés par des chercheurs et universitaires. 100% gratuit et sans publicité.",
        "icon_url": "https://www.google.com/s2/favicons?domain=theconversation.com&sz=128",
        "category": "Science & Climat",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": False,
        "factuality_rating": "Very High",
        "bias_rating": "Center",
        "media_type": "Analyse",
        "tags": ["Recherche", "Vulgarisation", "Université", "Science", "Société"],
    },
    {
        "url": "https://www.slate.fr/rss.xml",
        "site_url": "https://www.slate.fr",
        "title": "Slate.fr – Analyses & Décryptages",
        "description": "Slate.fr, magazine d'actualité en ligne. Analyses, décryptages et regards décalés sur l'actualité française et internationale.",
        "icon_url": "https://www.google.com/s2/favicons?domain=slate.fr&sz=128",
        "category": "Actualités & Presse",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": False,
        "factuality_rating": "High",
        "bias_rating": "Left-Center",
        "media_type": "Analyse",
        "tags": ["Analyse", "Société", "France", "International", "Décryptage"],
    },
    {
        "url": "https://www.courrierinternational.com/feed/all/rss.xml",
        "site_url": "https://www.courrierinternational.com",
        "title": "Courrier International – À la une",
        "description": "Revue de presse mondiale. Traduit et sélectionne chaque semaine les meilleurs articles de la presse étrangère.",
        "icon_url": "https://www.google.com/s2/favicons?domain=courrierinternational.com&sz=128",
        "category": "International & Monde",
        "language": "fr",
        "country": "FR",
        "is_verified": True,
        "is_jti_certified": False,
        "factuality_rating": "High",
        "bias_rating": "Center",
        "media_type": "Presse écrite",
        "tags": ["International", "Revue de presse", "Monde", "Traduction"],
    },
]

def seed():
    added = 0
    updated = 0
    for f in FEEDS:
        tags = f.pop("tags", [])
        # Store extra trust fields separately (add_or_update_catalog_feed handles base fields)
        trust_fields = {
            "is_jti_certified": f.pop("is_jti_certified", False),
            "factuality_rating": f.pop("factuality_rating", None),
            "bias_rating": f.pop("bias_rating", None),
            "media_type": f.pop("media_type", None),
        }
        feed_id = add_or_update_catalog_feed(f, tags)

        if feed_id:
            # Directly update trust columns
            from app.database import get_db_connection
            conn = get_db_connection()
            conn.execute("""
                UPDATE catalog_feeds SET
                    is_jti_certified = ?,
                    factuality_rating = ?,
                    bias_rating = ?,
                    media_type = ?
                WHERE id = ?
            """, (
                1 if trust_fields["is_jti_certified"] else 0,
                trust_fields["factuality_rating"],
                trust_fields["bias_rating"],
                trust_fields["media_type"],
                feed_id,
            ))
            conn.commit()
            conn.close()
            added += 1
            print(f"  [OK] {f['title']}")
        else:
            print(f"  [SKIP] {f.get('url')}")

    print(f"\nDone! {added} feeds added/updated in catalog.")

if __name__ == "__main__":
    seed()
