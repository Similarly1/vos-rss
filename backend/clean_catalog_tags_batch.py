import sqlite3
import unicodedata
import re

def normalize_tag(tag):
    tag = tag.strip().lower()
    tag = tag.replace('#', '')
    # Remove accents
    tag = ''.join(c for c in unicodedata.normalize('NFD', tag)
                  if unicodedata.category(c) != 'Mn')
    
    # Mapping to standard tags
    mapping = {
        'actualite': 'actualite',
        'news': 'actualite',
        'info': 'actualite',
        'presse': 'actualite',
        
        'business___economy': 'economie',
        'economie': 'economie',
        'business': 'economie',
        
        'cyber_security': 'cybersecurite',
        'cybersécurité': 'cybersecurite',
        'cybersecurite': 'cybersecurite',
        'securite': 'cybersecurite',
        'hacker': 'cybersecurite',
        
        'technologie': 'tech',
        'tech': 'tech',
        'hardware': 'tech',
        'innovation': 'tech',
        'linux': 'tech',
        
        'web_development': 'developpement',
        'developpement': 'developpement',
        'code': 'developpement',
        'programming': 'developpement',
        'open_source': 'developpement',
        
        'environment': 'environnement',
        'environnement': 'environnement',
        
        'space': 'science',
        'espace': 'science',
        'science': 'science',
        'recherche': 'science',
        'universite': 'science',
        
        'societe': 'societe',
        'droits_humains': 'societe',
        
        'chretien': 'chretien',
        'catholique': 'chretien',
        'protestant': 'chretien',
        'evangelique': 'chretien',
        'foi': 'chretien',
        'vatican': 'chretien',
        
        'suisse': 'suisse',
        'vaud': 'suisse',
        'fribourg': 'suisse',
        
        'monde': 'monde',
        'international': 'monde',
        
        'gaming': 'gaming',
        'culture': 'culture',
        'pop_culture': 'culture'
    }
    
    if tag in mapping:
        return mapping[tag]
    return tag

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import get_db_connection

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Mise au propre des tags existants...")
    
    # 1. Fetch all catalog feeds
    feeds = cursor.execute("SELECT id, url, title, description, category FROM catalog_feeds").fetchall()
    
    # 2. Get existing feed tags
    cursor.execute("""
        SELECT cf.id, t.name 
        FROM catalog_feeds cf
        JOIN catalog_feed_tags cft ON cf.id = cft.catalog_feed_id
        JOIN tags t ON cft.tag_id = t.id
    """)
    feed_tag_rows = cursor.fetchall()
    
    feed_tags = {}
    for feed_id, tag_name in feed_tag_rows:
        if feed_id not in feed_tags:
            feed_tags[feed_id] = set()
        feed_tags[feed_id].add(normalize_tag(tag_name))
        
    # Categories mapping to auto-assign tags if none or few
    cat_tag_map = {
        'Actualités': 'actualite',
        'Technologie': 'tech',
        'Économie': 'economie',
        'Science': 'science',
        'Sport': 'sport',
        'Monde': 'monde',
        'Culture': 'culture',
        'Santé': 'sante'
    }
    
    # Wipe existing tags
    cursor.execute("DELETE FROM catalog_feed_tags")
    cursor.execute("DELETE FROM tags")
    
    # Prepare inserts
    all_final_tags = set()
    feed_to_final_tags = {}
    
    for feed in feeds:
        f_id, url, title, desc, cat = feed
        tags = feed_tags.get(f_id, set())
        
        # Heuristics based on URL, title, desc
        text = f"{url} {title} {desc}".lower()
        if 'rts.ch' in text or 'suisse' in text or 'ch.rss' in text or 'letemps.ch' in text:
            tags.add('suisse')
        if 'tech' in text or 'informatique' in text:
            tags.add('tech')
        if 'science' in text or 'espace' in text:
            tags.add('science')
        if 'politique' in text:
            tags.add('politique')
        if 'cyber' in text or 'securite' in text or 'hacker' in text:
            tags.add('cybersecurite')
        if 'environn' in text or 'climat' in text or 'ecolo' in text:
            tags.add('environnement')
        if 'economie' in text or 'business' in text or 'finance' in text:
            tags.add('economie')
        if 'culture' in text or 'art' in text or 'cinema' in text:
            tags.add('culture')
        if 'monde' in text or 'international' in text:
            tags.add('monde')
        if 'chretien' in text or 'catholique' in text or 'protestant' in text or 'vatican' in text:
            tags.add('chretien')
            
        # Add category base tag
        if cat in cat_tag_map:
            tags.add(cat_tag_map[cat])
            
        # Filter empty tags
        tags = {t for t in tags if t}
        
        feed_to_final_tags[f_id] = tags
        all_final_tags.update(tags)
        
    # Insert new tags
    tag_id_map = {}
    for tag in all_final_tags:
        slug = tag
        cursor.execute("INSERT INTO tags (name, slug) VALUES (?, ?)", (tag, slug))
        tag_id_map[tag] = cursor.lastrowid
        
    # Insert mappings
    for f_id, tags in feed_to_final_tags.items():
        for tag in tags:
            t_id = tag_id_map[tag]
            cursor.execute("INSERT INTO catalog_feed_tags (catalog_feed_id, tag_id) VALUES (?, ?)", (f_id, t_id))
            
    conn.commit()
    print(f"Tags nettoyés et normalisés pour {len(feeds)} flux (total {len(all_final_tags)} tags uniques).")
    conn.close()

if __name__ == '__main__':
    main()
