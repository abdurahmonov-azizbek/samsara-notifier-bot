import asyncio
from src.functions import sync_trucks, send_auto_notifications
from src.logger import logger

async def sync_trucks_periodically():
    while True:
        logger.info("Running truck synchronization...")
        await sync_trucks()  
        # await asyncio.sleep(3600)
        await asyncio.sleep(120)  

async def send_auto_notifications_job():
    while True:
        logger.info("Running sending auto notifications....")
        await send_auto_notifications()
        await asyncio.sleep(60)