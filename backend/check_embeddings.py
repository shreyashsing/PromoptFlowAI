#!/usr/bin/env python3
"""Check if connectors have embeddings in the database."""

import asyncio
from app.core.database import get_database
from app.core.logging_config import init_logging

async def check_embeddings():
    """Check if connectors have embeddings stored."""
    init_logging()
    db = await get_database()
    result = db.table('connectors').select('name, embedding').execute()
    
    print('Connectors in database:')
    for row in result.data:
        has_embedding = row.get('embedding') is not None
        embedding_length = len(row.get('embedding', [])) if row.get('embedding') else 0
        print(f'  - {row["name"]}: embedding={has_embedding}, length={embedding_length}')

if __name__ == "__main__":
    asyncio.run(check_embeddings())