import asyncio
from datetime import datetime

import pytz
from fastapi import FastAPI, Request
from logger import logger
from uvicorn import Config, Server

from base import bot, dp
from handlers.admin_handler import router as admin_router
from handlers.base_handler import router as base_router
from handlers.startpoint_handler import router as startpoint_router
from handlers.user_handler import router as user_router
from jobs import sync_trucks_periodically
from src.jobs import send_auto_notifications, send_auto_notifications_job
from src.services.notification_service import get_notification_type_id, get_telegram_ids

app = FastAPI()

dp.include_router(startpoint_router)
dp.include_router(base_router)
dp.include_router(admin_router)
dp.include_router(user_router)


@app.post("/webhook/samsara")
async def samsara_webhook(request: Request):
    payload = await request.json()
    logger.info(f"Samsara webhook received: {payload}")

    event_type = payload.get("eventType")
    vehicle_id = payload.get("data", {}).get("data", {}).get("vehicle", {}).get("id", "Unknown")
    start_time = payload.get("data", {}).get("data", {}).get("startTime", "Unknown")

    if start_time != "Unknown":
        utc_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        est_timezone = pytz.timezone("America/New_York")
        est_time = utc_time.astimezone(est_timezone)
        formatted_time = est_time.strftime("%Y-%m-%d %I:%M:%S %p %Z")
    else:
        formatted_time = "Unknown"

    try:
        notification_type_id = await get_notification_type_id(event_type)
        logger.info(f"Detected notification_type_id: {notification_type_id} for event {event_type}")

        telegram_data = await get_telegram_ids(vehicle_id, notification_type_id)

        if telegram_data:
            message_text = (
                f"🚨 *Samsara Alert* 🚨\n"
                f"📢 *Event*: {event_type}\n"
                f"⏰ *Start Time*: {formatted_time}\n"
            )

            for telegram_id, truck_name in telegram_data:
                full_message = f"{message_text}\n🚛 *Truck Name*: {truck_name}"
                await bot.send_message(chat_id=telegram_id, text=full_message, parse_mode="Markdown")
            logger.info(f"Notification sent to Telegram for vehicle {vehicle_id}, type {notification_type_id}")
        else:
            logger.info(f"No notification configured for vehicle {vehicle_id} and type {notification_type_id}")
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")

    return {"status": "success", "message": "Webhook processed"}


async def run_fastapi():
    config = Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = Server(config)
    await server.serve()


async def main():
    logger.info("Starting...")

    asyncio.create_task(sync_trucks_periodically())

    asyncio.create_task(send_auto_notifications_job())

    asyncio.create_task(run_fastapi())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
