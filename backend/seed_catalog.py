import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from seed_massive_catalog import seed_massive_catalog_async, seed_catalog

if __name__ == "__main__":
    seed_catalog()
