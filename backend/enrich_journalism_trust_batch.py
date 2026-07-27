import sqlite3
import os
import sys
from pathlib import Path

db_path = Path(__file__).parent / "vos.db"

def get_db():
    return sqlite3.connect(db_path)

def enrich_trust_metadata():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Known JTI Certified Domains (RSF)
    jti_certified_domains = [
        'rts.ch', 'bbc.co.uk', 'bbc.com', 'lemonde.fr', 'afp.com', 
        'theguardian.com', 'reuters.com', 'apnews.com', 'la-croix.com', 'letemps.ch'
    ]

    # Specific Domain / Title Mappings
    specific_rules = [
        # Agence / Factuel / Centre
        {"pattern": "afp.com", "factuality": "Very High", "bias": "Center", "type": "Agence"},
        {"pattern": "reuters.com", "factuality": "Very High", "bias": "Center", "type": "Agence"},
        {"pattern": "apnews.com", "factuality": "Very High", "bias": "Center", "type": "Agence"},
        {"pattern": "cert.ssi.gouv.fr", "factuality": "Very High", "bias": "Center", "type": "Agence"},
        {"pattern": "vaticannews.va", "factuality": "High", "bias": "Center", "type": "Général"},

        # Suisse
        {"pattern": "rts.ch", "factuality": "High", "bias": "Center", "type": "Régional"},
        {"pattern": "blick.ch", "factuality": "High", "bias": "Center", "type": "Régional"},
        {"pattern": "letemps.ch", "factuality": "High", "bias": "Center", "type": "Analyse"},
        {"pattern": "nzz.ch", "factuality": "High", "bias": "Right-Center", "type": "Analyse"},
        {"pattern": "latele.ch", "factuality": "High", "bias": "Center", "type": "Régional"},
        {"pattern": "surgir.ch", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "tagesanzeiger.ch", "factuality": "High", "bias": "Center", "type": "Régional"},
        {"pattern": "reformes.ch", "factuality": "High", "bias": "Center", "type": "Général"},

        # Presse & Monde
        {"pattern": "lemonde.fr", "factuality": "High", "bias": "Left-Center", "type": "Général"},
        {"pattern": "mediapart.fr", "factuality": "High", "bias": "Left", "type": "Analyse"},
        {"pattern": "theguardian.com", "factuality": "High", "bias": "Left-Center", "type": "Général"},
        {"pattern": "bbc.", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "theconversation.com", "factuality": "High", "bias": "Center", "type": "Analyse"},
        {"pattern": "courrierinternational.com", "factuality": "High", "bias": "Center", "type": "Analyse"},
        {"pattern": "elpais.com", "factuality": "High", "bias": "Left-Center", "type": "Général"},
        {"pattern": "spiegel.de", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "la-croix.com", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "lefigaro.fr", "factuality": "High", "bias": "Right-Center", "type": "Général"},

        # Tech & Science
        {"pattern": "next.ink", "factuality": "High", "bias": "Left-Center", "type": "Analyse"},
        {"pattern": "numerama.com", "factuality": "High", "bias": "Center", "type": "Analyse"},
        {"pattern": "korben.info", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "techcrunch.com", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "arstechnica.com", "factuality": "High", "bias": "Center", "type": "Analyse"},
        {"pattern": "ycombinator.com", "factuality": "High", "bias": "Center", "type": "Analyse"},
        {"pattern": "nature.com", "factuality": "Very High", "bias": "Center", "type": "Analyse"},

        # Religion / Chrétien
        {"pattern": "christianismeaujourdhui.info", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "evangeliques.info", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "regardsprotestants.com", "factuality": "High", "bias": "Center", "type": "Général"},
        {"pattern": "christianitytoday.com", "factuality": "High", "bias": "Right-Center", "type": "Analyse"},
    ]

    try:
        # Step 1: Default intelligent fallback for ALL feeds
        cursor.execute("""
            UPDATE catalog_feeds
            SET is_jti_certified = 0,
                factuality_rating = 'High',
                bias_rating = 'Center',
                media_type = 'Général'
        """)

        # Step 2: Apply specific rules by URL or title
        for rule in specific_rules:
            pat = f"%{rule['pattern']}%"
            is_jti = 1 if any(j_dom in rule['pattern'] for j_dom in jti_certified_domains) else 0

            cursor.execute("""
                UPDATE catalog_feeds
                SET is_jti_certified = ?,
                    factuality_rating = ?,
                    bias_rating = ?,
                    media_type = ?
                WHERE url LIKE ? OR site_url LIKE ? OR title LIKE ?
            """, (is_jti, rule['factuality'], rule['bias'], rule['type'], pat, pat, pat))

        # Step 3: Heuristic auto-tagging for remaining feeds based on category & text
        cursor.execute("SELECT id, url, site_url, title, category FROM catalog_feeds")
        rows = cursor.fetchall()
        for r in rows:
            f_id = r["id"]
            text = f"{r['url']} {r['site_url']} {r['title']} {r['category']}".lower()
            
            # Check JTI certification
            is_jti = 1 if any(j_dom in text for j_dom in jti_certified_domains) else 0
            
            # Media type heuristics
            m_type = "Général"
            if "agence" in text or "afp" in text or "reuters" in text or "anssi" in text or "cert" in text:
                m_type = "Agence"
            elif "analyse" in text or "review" in text or "tech" in text or "science" in text or "nature" in text:
                m_type = "Analyse"
            elif "suisse" in text or "tele" in text or "journal" in text or "local" in text:
                m_type = "Régional"

            # Bias heuristics
            m_bias = "Center"
            if "mediapart" in text or "guardian" in text or "lemonde" in text or "gauche" in text:
                m_bias = "Left-Center"
            elif "figaro" in text or "nzz" in text or "wsj" in text or "droite" in text or "business" in text:
                m_bias = "Right-Center"

            cursor.execute("""
                UPDATE catalog_feeds
                SET is_jti_certified = MAX(is_jti_certified, ?),
                    media_type = CASE WHEN media_type = 'Général' THEN ? ELSE media_type END,
                    bias_rating = CASE WHEN bias_rating = 'Center' THEN ? ELSE bias_rating END
                WHERE id = ?
            """, (is_jti, m_type, m_bias, f_id))

        conn.commit()
        print("Successfully enriched journalism trust metadata for 100% of catalog feeds.")
    except Exception as e:
        print(f"Error enriching metadata: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    enrich_trust_metadata()
