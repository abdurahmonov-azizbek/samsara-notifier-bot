import asyncpg
import config

async def get_db_connection():
    return await asyncpg.connect(**config.DB_CONFIG)

