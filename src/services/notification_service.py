from src import  db
from src.models import Notification
from src.logger import  logger
from src import  constants

async def create_auto_notification(notification: Notification):
    try:
        conn = await db.get_db_connection()
        query = f"INSERT INTO {constants.NOTIFICATION_TABLE} (telegram_id, truck_id, notification_type_id, every_minutes) VALUES ($1, $2, $3, $4)"

        await conn.execute(
            query,
            notification.telegram_id,
            notification.truck_id,
            3,
            notification.every_minutes)

        return True
    except Exception as e:
        logger.error(f"Error while creating auto notification: {e}")
    finally:
        await conn.close()