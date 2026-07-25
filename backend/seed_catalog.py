import os
import sys

# Ensure backend root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db
from app.services.catalog import add_or_update_catalog_feed

SEED_FEEDS = [
    # 🇨🇭 SUISSE
    {
        "url": "https://www.rts.ch/info/toute-info/?format=rss/news",
        "site_url": "https://www.rts.ch/info/",
        "title": "RTS Info (Radio Télévision Suisse)",
        "description": "Actualité suisse et internationale en continu par le service public RTS.",
        "icon_url": "https://www.google.com/s2/favicons?domain=rts.ch&sz=128",
        "category": "Suisse",
        "language": "fr",
        "country": "CH",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#suisse", "#actualité", "#média"]
    },
    {
        "url": "https://www.letemps.ch/feed",
        "site_url": "https://www.letemps.ch",
        "title": "Le Temps (Suisse)",
        "description": "Le quotidien suisse francophone de référence sur la politique, l'économie et la culture.",
        "icon_url": "https://www.google.com/s2/favicons?domain=letemps.ch&sz=128",
        "category": "Suisse",
        "language": "fr",
        "country": "CH",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#suisse", "#presse", "#économie"]
    },
    {
        "url": "https://latele.ch/feed",
        "site_url": "https://latele.ch",
        "title": "La Télé (Vaud & Fribourg)",
        "description": "La télévision régionale de Suisse romande couvrant l'actualité vaudoise et fribourgeoise.",
        "icon_url": "https://www.google.com/s2/favicons?domain=latele.ch&sz=128",
        "category": "Suisse",
        "language": "fr",
        "country": "CH",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#suisse", "#vaud", "#fribourg", "#média"]
    },
    {
        "url": "https://www.blick.ch/fr/rss.xml",
        "site_url": "https://www.blick.ch/fr",
        "title": "Blick (Suisse)",
        "description": "L'actualité suisse et internationale traitée en direct par le média Blick en français.",
        "icon_url": "https://www.google.com/s2/favicons?domain=blick.ch&sz=128",
        "category": "Suisse",
        "language": "fr",
        "country": "CH",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#suisse", "#actualité", "#presse"]
    },
    {
        "url": "https://www.nzz.ch/recent.rss",
        "site_url": "https://www.nzz.ch",
        "title": "Neue Zürcher Zeitung (NZZ)",
        "description": "Quotidien suisse alémanique indépendant et de haute qualité journalistique.",
        "icon_url": "https://www.google.com/s2/favicons?domain=nzz.ch&sz=128",
        "category": "Suisse",
        "language": "de",
        "country": "CH",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#suisse", "#allemand", "#économie"]
    },

    {
        "url": "https://surgir.ch/feed",
        "site_url": "https://surgir.ch",
        "title": "Surgir (Fondation)",
        "description": "Fondation suisse engagée pour la défense des droits humains et la lutte contre les violences faites aux femmes.",
        "icon_url": "https://www.google.com/s2/favicons?domain=surgir.ch&sz=128",
        "category": "Suisse",
        "language": "fr",
        "country": "CH",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#suisse", "#société", "#droits_humains"]
    },

    # 🌍 MONDE & GENERAL
    {
        "url": "https://www.lemonde.fr/rss/une.xml",
        "site_url": "https://www.lemonde.fr",
        "title": "Le Monde (À la une)",
        "description": "Journal d'information générale de référence en France et en francophonie.",
        "icon_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=128",
        "category": "Monde",
        "language": "fr",
        "country": "FR",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#france", "#presse"]
    },
    {
        "url": "https://www.mediapart.fr/articles/feed",
        "site_url": "https://www.mediapart.fr",
        "title": "Mediapart",
        "description": "Journal d'information numérique indépendant et participatif.",
        "icon_url": "https://www.google.com/s2/favicons?domain=mediapart.fr&sz=128",
        "category": "Monde",
        "language": "fr",
        "country": "FR",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#france", "#enquête"]
    },
    {
        "url": "https://theconversation.com/fr/articles.atom",
        "site_url": "https://theconversation.com/fr",
        "title": "The Conversation France",
        "description": "Analyses et informations rédigées par des universitaires et chercheurs. Flux 100% natif complet.",
        "icon_url": "https://www.google.com/s2/favicons?domain=theconversation.com&sz=128",
        "category": "Monde",
        "language": "fr",
        "country": "FR",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#monde", "#science", "#université"]
    },
    {
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "site_url": "https://www.bbc.com/news/world",
        "title": "BBC News World",
        "description": "Actualités internationales de la British Broadcasting Corporation en direct.",
        "icon_url": "https://www.google.com/s2/favicons?domain=bbc.com&sz=128",
        "category": "Monde",
        "language": "en",
        "country": "UK",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#anglais", "#actualité"]
    },
    {
        "url": "https://www.theguardian.com/world/rss",
        "site_url": "https://www.theguardian.com/world",
        "title": "The Guardian World",
        "description": "Le quotidien indépendant britannique couvrant les enjeux globaux et le climat.",
        "icon_url": "https://www.google.com/s2/favicons?domain=theguardian.com&sz=128",
        "category": "Monde",
        "language": "en",
        "country": "UK",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#anglais", "#presse"]
    },
    {
        "url": "https://www.courrierinternational.com/feed/all/rss.xml",
        "site_url": "https://www.courrierinternational.com",
        "title": "Courrier International",
        "description": "Le meilleur de la presse étrangère traduit en français.",
        "icon_url": "https://www.google.com/s2/favicons?domain=courrierinternational.com&sz=128",
        "category": "Monde",
        "language": "fr",
        "country": "FR",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#presse", "#international"]
    },
    {
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "site_url": "https://elpais.com",
        "title": "El País Portada",
        "description": "Premier quotidien généraliste espagnol et mondial en langue espagnole.",
        "icon_url": "https://www.google.com/s2/favicons?domain=elpais.com&sz=128",
        "category": "Monde",
        "language": "es",
        "country": "ES",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#espagnol", "#presse"]
    },
    {
        "url": "https://www.spiegel.de/schlagzeilen/index.rss",
        "site_url": "https://www.spiegel.de",
        "title": "Der Spiegel (Schlagzeilen)",
        "description": "Premier magazine d'information en Allemagne sur la politique et la société.",
        "icon_url": "https://www.google.com/s2/favicons?domain=spiegel.de&sz=128",
        "category": "Monde",
        "language": "de",
        "country": "DE",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#monde", "#allemand", "#presse"]
    },

    # 🚀 TECHNOLOGIE & NUMÉRIQUE
    {
        "url": "https://next.ink/feed/",
        "site_url": "https://next.ink",
        "title": "Next.ink (Tech & Numérique)",
        "description": "Média indépendant spécialisé dans le numérique, les libertés et l'informatique. Contenu complet natif.",
        "icon_url": "https://www.google.com/s2/favicons?domain=next.ink&sz=128",
        "category": "Technologie",
        "language": "fr",
        "country": "FR",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#technologie", "#numérique", "#open_source"]
    },
    {
        "url": "https://www.numerama.com/feed/",
        "site_url": "https://www.numerama.com",
        "title": "Numerama",
        "description": "Actualités de la société numérique, pop-culture, sciences et mobilité.",
        "icon_url": "https://www.google.com/s2/favicons?domain=numerama.com&sz=128",
        "category": "Technologie",
        "language": "fr",
        "country": "FR",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#technologie", "#pop_culture", "#science"]
    },
    {
        "url": "https://korben.info/feed",
        "site_url": "https://korben.info",
        "title": "Korben.info",
        "description": "Blog incontournable sur le bidouillage, la cybersécurité, les logiciels libres et la tech.",
        "icon_url": "https://www.google.com/s2/favicons?domain=korben.info&sz=128",
        "category": "Technologie",
        "language": "fr",
        "country": "FR",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#technologie", "#hacker", "#open_source"]
    },
    {
        "url": "https://www.cert.ssi.gouv.fr/feed/",
        "site_url": "https://www.cert.ssi.gouv.fr",
        "title": "CERT-FR (ANSSI Cybersécurité)",
        "description": "Avis de sécurité et alertes officielles de l'Agence Nationale de la Sécurité des Systèmes d'Information.",
        "icon_url": "https://www.google.com/s2/favicons?domain=cert.ssi.gouv.fr&sz=128",
        "category": "Technologie",
        "language": "fr",
        "country": "FR",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#cybersécurité", "#technologie", "#sécurité"]
    },
    {
        "url": "https://techcrunch.com/feed/",
        "site_url": "https://techcrunch.com",
        "title": "TechCrunch",
        "description": "L'actualité mondiale de référence sur les startups, le capital-risque et la Silicon Valley.",
        "icon_url": "https://www.google.com/s2/favicons?domain=techcrunch.com&sz=128",
        "category": "Technologie",
        "language": "en",
        "country": "US",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#technologie", "#startups", "#anglais"]
    },
    {
        "url": "http://feeds.arstechnica.com/arstechnica/index",
        "site_url": "https://arstechnica.com",
        "title": "Ars Technica",
        "description": "Analyses approfondies en informatique, politiques publiques de la tech et sciences.",
        "icon_url": "https://www.google.com/s2/favicons?domain=arstechnica.com&sz=128",
        "category": "Technologie",
        "language": "en",
        "country": "US",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#technologie", "#science", "#anglais"]
    },
    {
        "url": "https://news.ycombinator.com/rss",
        "site_url": "https://news.ycombinator.com",
        "title": "Hacker News",
        "description": "Le fil d'actualités communautaire des développeurs et fondateurs d'entreprises par Y Combinator.",
        "icon_url": "https://www.google.com/s2/favicons?domain=ycombinator.com&sz=128",
        "category": "Technologie",
        "language": "en",
        "country": "US",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#technologie", "#développement", "#startups"]
    },

    # ⛪ CHRÉTIEN
    {
        "url": "https://www.la-croix.com/feeds/rss/site.xml",
        "site_url": "https://www.la-croix.com",
        "title": "La Croix",
        "description": "Grand quotidien catholique français traitant de l'actualité générale, religieuse et spirituelle.",
        "icon_url": "https://www.google.com/s2/favicons?domain=la-croix.com&sz=128",
        "category": "Chrétien",
        "language": "fr",
        "country": "FR",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#chrétien", "#foi", "#actualité", "#presse"]
    },
    {
        "url": "https://www.christianismeaujourdhui.info/feed/",
        "site_url": "https://www.christianismeaujourdhui.info",
        "title": "Le Christianisme Aujourd'hui",
        "description": "Magazine francophone protestant sur l'actualité du christianisme, de la société et de la foi.",
        "icon_url": "https://www.google.com/s2/favicons?domain=christianismeaujourdhui.info&sz=128",
        "category": "Chrétien",
        "language": "fr",
        "country": "FR",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#chrétien", "#protestant", "#foi", "#société"]
    },
    {
        "url": "https://www.evangeliques.info/feed/",
        "site_url": "https://www.evangeliques.info",
        "title": "Evangeliques.info",
        "description": "Portail d'information francophone sur la foi chrétienne évangélique et les questions éthiques.",
        "icon_url": "https://www.google.com/s2/favicons?domain=evangeliques.info&sz=128",
        "category": "Chrétien",
        "language": "fr",
        "country": "CH",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#chrétien", "#évangélique", "#actualité"]
    },
    {
        "url": "https://www.reformes.ch/rss.xml",
        "site_url": "https://www.reformes.ch",
        "title": "Réformés.ch (Suisse)",
        "description": "Le journal des Églises réformées de Suisse romande (Vaud, Genève, Neuchâtel, Berne-Jura-Neuchâtel).",
        "icon_url": "https://www.google.com/s2/favicons?domain=reformes.ch&sz=128",
        "category": "Chrétien",
        "language": "fr",
        "country": "CH",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#chrétien", "#suisse", "#protestant", "#foi"]
    },
    {
        "url": "https://www.vaticannews.va/fr.rss.xml",
        "site_url": "https://www.vaticannews.va/fr.html",
        "title": "Vatican News (Français)",
        "description": "L'information officielle du Saint-Siège et l'actualité de l'Église catholique dans le monde.",
        "icon_url": "https://www.google.com/s2/favicons?domain=vaticannews.va&sz=128",
        "category": "Chrétien",
        "language": "fr",
        "country": "VA",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#chrétien", "#catholique", "#vatican"]
    },
    {
        "url": "https://regardsprotestants.com/feed/",
        "site_url": "https://regardsprotestants.com",
        "title": "Regards Protestants",
        "description": "Plateforme réunissant les médias et podcasts du protestantisme francophone.",
        "icon_url": "https://www.google.com/s2/favicons?domain=regardsprotestants.com&sz=128",
        "category": "Chrétien",
        "language": "fr",
        "country": "FR",
        "is_full_text": True,
        "is_verified": True,
        "tags": ["#chrétien", "#protestant", "#médias"]
    },
    {
        "url": "https://www.christianitytoday.com/feed",
        "site_url": "https://www.christianitytoday.com",
        "title": "Christianity Today",
        "description": "Leading global evangelical media providing thoughtful commentary and global news.",
        "icon_url": "https://www.google.com/s2/favicons?domain=christianitytoday.com&sz=128",
        "category": "Chrétien",
        "language": "en",
        "country": "US",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#chrétien", "#anglais", "#foi"]
    },

    # 🔬 SCIENCE
    {
        "url": "http://feeds.nature.com/nature/rss/current",
        "site_url": "https://www.nature.com",
        "title": "Nature News",
        "description": "Les découvertes scientifiques majeures publiées dans la revue Nature.",
        "icon_url": "https://www.google.com/s2/favicons?domain=nature.com&sz=128",
        "category": "Science",
        "language": "en",
        "country": "UK",
        "is_full_text": False,
        "is_verified": True,
        "tags": ["#science", "#recherche", "#anglais"]
    }
]

def seed_catalog():
    print("[Catalogue Seed] Initialisation de la base de donnees...")
    init_db()
    
    # Clean up obsolete verified seed feeds that were removed from SEED_FEEDS
    valid_urls = {f["url"] for f in SEED_FEEDS}
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, url FROM catalog_feeds WHERE is_verified = 1")
        rows = cursor.fetchall()
        deleted_count = 0
        for r in rows:
            if r["url"] not in valid_urls:
                cursor.execute("DELETE FROM catalog_feeds WHERE id = ?", (r["id"],))
                cursor.execute("DELETE FROM catalog_feeds_fts WHERE catalog_feed_id = ?", (r["id"],))
                deleted_count += 1
        conn.commit()
        conn.close()
        if deleted_count > 0:
            print(f"[Catalogue Seed] Suppression de {deleted_count} flux mort/obsolete du catalogue.")
    except Exception as e:
        print(f"[Catalogue Cleanup note]: {e}")

    added_count = 0
    for feed_info in SEED_FEEDS:
        tags = feed_info.pop("tags", [])
        feed_id = add_or_update_catalog_feed(feed_info, tags=tags)
        if feed_id:
            added_count += 1

    print(f"[Catalogue Seed] [OK] {added_count} flux enregistres dans le catalogue initial.")

if __name__ == "__main__":
    seed_catalog()
