import sqlite3
import sys
from pathlib import Path

# Adjust path if needed
db_path = Path(__file__).parent / "vos.db"

def get_db():
    return sqlite3.connect(db_path)

def enrich_trust_metadata():
    conn = get_db()
    cursor = conn.cursor()
    
    # We define some mappings based on known domains / titles
    # JTI / RSF Certified (examples)
    jti_certified_domains = ['rts.ch', 'bbc.co.uk', 'bbc.com', 'lemonde.fr', 'afp.com', 'theguardian.com', 'reuters.com', 'apnews.com']
    
    # Factuality & Bias (examples from MBFC)
    metadata_rules = [
        {"domain": "rts.ch", "factuality": "High", "bias": "Center", "type": "Général"},
        {"domain": "bbc.co.uk", "factuality": "High", "bias": "Center", "type": "Général"},
        {"domain": "bbc.com", "factuality": "High", "bias": "Center", "type": "Général"},
        {"domain": "lemonde.fr", "factuality": "High", "bias": "Left-Center", "type": "Général"},
        {"domain": "afp.com", "factuality": "Very High", "bias": "Least Biased", "type": "Agence"},
        {"domain": "reuters.com", "factuality": "Very High", "bias": "Least Biased", "type": "Agence"},
        {"domain": "apnews.com", "factuality": "Very High", "bias": "Least Biased", "type": "Agence"},
        {"domain": "theguardian.com", "factuality": "Mixed", "bias": "Left", "type": "Général"},
        {"domain": "nytimes.com", "factuality": "High", "bias": "Left-Center", "type": "Général"},
        {"domain": "letemps.ch", "factuality": "High", "bias": "Center", "type": "Général"},
        {"domain": "tdg.ch", "factuality": "High", "bias": "Center", "type": "Régional"},
        {"domain": "24heures.ch", "factuality": "High", "bias": "Center", "type": "Régional"},
        {"domain": "mediapart.fr", "factuality": "High", "bias": "Left", "type": "Analyse"},
        {"domain": "monde-diplomatique.fr", "factuality": "High", "bias": "Left", "type": "Analyse"},
    ]
    
    try:
        # Default fallback updates for ALL feeds first
        cursor.execute("""
            UPDATE catalog_feeds
            SET is_jti_certified = 0,
                factuality_rating = 'Unrated',
                bias_rating = 'Unknown',
                media_type = 'Général'
            WHERE is_jti_certified IS NULL
               OR factuality_rating IS NULL
               OR bias_rating IS NULL
               OR media_type IS NULL
        """)
        
        # Apply specific rules
        for rule in metadata_rules:
            domain = f"%{rule['domain']}%"
            
            is_jti = 1 if rule['domain'] in jti_certified_domains else 0
            
            cursor.execute("""
                UPDATE catalog_feeds
                SET is_jti_certified = ?,
                    factuality_rating = ?,
                    bias_rating = ?,
                    media_type = ?
                WHERE url LIKE ? OR site_url LIKE ?
            """, (is_jti, rule['factuality'], rule['bias'], rule['type'], domain, domain))
            
        conn.commit()
        print("Successfully enriched journalism trust metadata in catalog_feeds.")
    except Exception as e:
        print(f"Error updating metadata: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    enrich_trust_metadata()
