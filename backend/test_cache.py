import asyncio
from app.database import init_db
from app.services.clustering import precompute_and_cache_clusters, get_cached_clusters

init_db()

async def main():
    print("Execution du pré-calcul des clusters...")
    res = await precompute_and_cache_clusters()
    print("Résultat du pré-calcul :", res)
    events = get_cached_clusters("threshold_events")
    print("Nombre d'événements en cache :", len(events) if events else 0)

asyncio.run(main())
