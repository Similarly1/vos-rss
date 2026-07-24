import sqlite3
from pathlib import Path

try:
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False

DB_PATH = Path("./vos.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    if HAS_SQLITE_VEC:
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception as e:
            print(f"[Attention] Impossible de charger l'extension sqlite-vec: {e}")
            
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Feeds table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        title TEXT,
        category TEXT,
        language TEXT DEFAULT 'fr',
        is_full_text INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Articles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feed_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        url TEXT UNIQUE NOT NULL,
        published_date TIMESTAMP,
        image_url TEXT,
        language TEXT DEFAULT 'fr',
        is_full_text INTEGER DEFAULT 1,
        FOREIGN KEY (feed_id) REFERENCES feeds (id)
    )
    ''')

    # Auto-migration for feeds columns
    try:
        cursor.execute("PRAGMA table_info(feeds)")
        feed_cols = [row["name"] for row in cursor.fetchall()]
        if feed_cols:
            if "language" not in feed_cols:
                cursor.execute("ALTER TABLE feeds ADD COLUMN language TEXT DEFAULT 'fr'")
            if "is_full_text" not in feed_cols:
                cursor.execute("ALTER TABLE feeds ADD COLUMN is_full_text INTEGER DEFAULT 1")
    except Exception as e:
        print(f"[Migration note] feeds columns check: {e}")

    # Auto-migration for articles columns
    try:
        cursor.execute("PRAGMA table_info(articles)")
        art_cols = [row["name"] for row in cursor.fetchall()]
        if art_cols:
            if "image_url" not in art_cols:
                cursor.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")
            if "language" not in art_cols:
                cursor.execute("ALTER TABLE articles ADD COLUMN language TEXT DEFAULT 'fr'")
            if "is_full_text" not in art_cols:
                cursor.execute("ALTER TABLE articles ADD COLUMN is_full_text INTEGER DEFAULT 1")
    except Exception as e:
        print(f"[Migration note] articles columns check: {e}")

    # 3. Main Embeddings storage table
    try:
        cursor.execute("PRAGMA table_info(article_embeddings)")
        columns = [row["name"] for row in cursor.fetchall()]
        if columns and "embedding_json" not in columns:
            cursor.execute("DROP TABLE IF EXISTS article_embeddings")
    except Exception:
        cursor.execute("DROP TABLE IF EXISTS article_embeddings")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS article_embeddings (
        article_id INTEGER PRIMARY KEY,
        embedding_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles (id)
    )
    ''')

    # 4. Podcasts History table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS podcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        script TEXT NOT NULL,
        audio_filename TEXT NOT NULL,
        audio_url TEXT NOT NULL,
        image_url TEXT,
        topics_count INTEGER DEFAULT 5,
        max_days INTEGER DEFAULT 7,
        only_verified INTEGER DEFAULT 0,
        voice TEXT DEFAULT 'marie',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 5. Pre-calculated Cluster & Synthesis Cache Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cluster_cache (
        threshold_key TEXT PRIMARY KEY,
        clusters_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 6. App Settings Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')

    # Auto-migration for podcasts image_url column
    try:
        cursor.execute("PRAGMA table_info(podcasts)")
        pod_cols = [row["name"] for row in cursor.fetchall()]
        if pod_cols and "image_url" not in pod_cols:
            cursor.execute("ALTER TABLE podcasts ADD COLUMN image_url TEXT")
    except Exception as e:
        print(f"[Migration note] podcasts image_url check: {e}")

    # 7. sqlite-vec virtual table
    if HAS_SQLITE_VEC:
        try:
            cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_articles USING vec0(
                article_id integer primary key,
                embedding float[1024]
            )
            ''')
        except Exception as e:
            print(f"[Attention] Note sur vec0: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
