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
from src.jobs import send_auto_notifications_job
from src.services.notification_service import get_notification_type_id, get_telegram_ids
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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
    vehicle_id = None
    start_time = None
    description = event_type
    is_resolved = False

    if event_type == "AlertIncident":
        conditions = payload.get("data", {}).get("conditions", [])
        if not conditions:
            logger.error("No conditions found in AlertIncident payload")
            return {"status": "error", "message": "No conditions in payload"}

        condition_details = conditions[0].get("details", {})
        event_type = list(condition_details.keys())[0]
        description = conditions[0].get("description", "Unknown event")
        vehicle_id = condition_details.get(event_type, {}).get("vehicle", {}).get("id", "Unknown")
        start_time = payload.get("data", {}).get("happenedAtTime", "Unknown")
        is_resolved = payload.get("data", {}).get("isResolved", False)
        incidentUrl = payload.get("data", {}).get("incidentUrl", False)
    else:
        vehicle_id = payload.get("data", {}).get("data", {}).get("vehicle", {}).get("id", "Unknown")
        start_time = payload.get("data", {}).get("data", {}).get("startTime", "Unknown")

    if vehicle_id == "Unknown" or start_time == "Unknown":
        logger.error("Missing vehicle_id or start_time in payload")
        return {"status": "error", "message": "Invalid payload data"}

    utc_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    est_timezone = pytz.timezone("America/New_York")
    est_time = utc_time.astimezone(est_timezone)
    formatted_time = est_time.strftime("%Y-%m-%d %I:%M:%S %p")

    try:
        notification_type_id = await get_notification_type_id(event_type)
        logger.info(f"Detected notification_type_id: {notification_type_id} for event {event_type}")

        telegram_data = await get_telegram_ids(vehicle_id, notification_type_id, event_type)
        if telegram_data:
            if event_type == "deviceMovement":
                message_text = (
                    f"🚛 *Truck Started Moving* 🚛\n"
                    f"📢 *Event*: {description}\n"
                    f"⏰ *Time*: {formatted_time}\n"
                )
            elif event_type == "deviceMovementStopped":
                message_text = (
                    f"🛑 *Truck Stopped Moving* 🛑\n"
                    f"📢 *Event*: {description}\n"
                    f"⏰ *Time*: {formatted_time}\n"
                )
            elif event_type == "harshEvent":
                message_text = (
                    f"⚠️ *Harsh Driving Detected* ⚠️\n"
                    f"📢 *Event*: {description}\n"
                    f"⏰ *Time*: {formatted_time}\n"
                )
            elif event_type == "SevereSpeedingStarted":
                message_text = (
                    f"🚨 *Severe Speeding Detected* 🚨\n"
                    f"📢 *Event*: {description}\n"
                    f"⏰ *Time*: {formatted_time}\n"
                )
            else:
                message_text = (
                    f"🚨 *Samsara Alert* 🚨\n"
                    f"📢 *Event*: {description}\n"
                    f"⏰ *Time*: {formatted_time}\n"
                )

            if is_resolved:
                message_text += "✅ *Status*: Resolved\n"

            for telegram_id, truck_name in set(telegram_data):
                full_message = f"{message_text}🚛 *Truck Name*: {truck_name}"
                if incidentUrl:
                    keyboard = [
                        [InlineKeyboardButton(text="Incident Details", url=incidentUrl)]
                    ]
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=full_message,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                else:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=full_message,
                        parse_mode="Markdown"
                    )
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
