import asyncio

from fastapi import FastAPI, Request
from logger import logger
from uvicorn import Config, Server

from base import bot, dp
from handlers.admin_handler import router as admin_router
from handlers.base_handler import router as base_router
from handlers.startpoint_handler import router as startpoint_router
from handlers.user_handler import router as user_router
from jobs import sync_trucks_periodically

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
    event_details = payload.get("event", {}).get("details", "No details")
    vehicle_id = payload.get("event", {}).get("device", {}).get("id", "Unknown")
    alert_condition = payload.get("event", {}).get("alertConditionId", "Unknown")

    message_text = (
        f"Samsara Alert:\n"
        f"Event: {event_type}\n"
        f"Condition: {alert_condition}\n"
        f"Vehicle ID: {vehicle_id}\n"
        f"Details: {event_details}"
    )
    print(message_text)

    try:
        logger.info("Notification sent to Telegram")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

    return {"status": "success", "message": "Webhook processed"}


async def run_fastapi():
    config = Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = Server(config)
    await server.serve()


async def main():
    logger.info("Starting...")

    asyncio.create_task(sync_trucks_periodically())

    asyncio.create_task(run_fastapi())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
