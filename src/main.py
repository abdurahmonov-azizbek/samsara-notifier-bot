from base import bot, dp
from logger import logger
import asyncio
from handlers.startpoint_handler import router as startpoint_router
from handlers.base_handler import router as base_router
from handlers.admin_handler import router as admin_router
from handlers.user_handler import router as user_router
from jobs import sync_trucks_periodically

dp.include_router(startpoint_router)
dp.include_router(base_router)
dp.include_router(admin_router)
dp.include_router(user_router)
async def main():
    logger.info("Starting...")
    asyncio.create_task(sync_trucks_periodically())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())