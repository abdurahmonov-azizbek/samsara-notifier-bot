import asyncio
from functions import sync_trucks
from logger import logger

async def sync_trucks_periodically():
    while True:
        logger.info("Running truck synchronization...")
        await sync_trucks()  
        # await asyncio.sleep(3600)
        await asyncio.sleep(120)  
