from src import  db
from src.models import Notification
from src.logger import  logger
from src import  constants
from typing import List

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

async def get_by_query(query: str) -> List[Notification]:
    try:
        conn = await db.get_db_connection()

        rows = await conn.fetch(query)
        notifications = [
            Notification(
                id=row['id'],
                telegram_id=row['telegram_id'],
                truck_id=row['truck_id'],
                notification_type_id=row['notification_type_id'],
                every_minutes=row['every_minutes'],
                last_send_time=row['last_send_time'],
                warning_type=row['warning_type'],
                engine_status=row['engine_status']
            )
            for row in rows]

        return notifications
    except Exception as e:
        logger.error(f"Error while fetchin notifications by query: {e}")
    finally:
        await conn.close()

async def update(notification: Notification):
    conn = await db.get_db_connection()
    query = f"UPDATE {constants.NOTIFICATION_TABLE} SET telegram_id = $1, truck_id = $2, notification_type_id = $3, every_minutes = $4, last_send_time = $5, warning_type = $6, engine_status = $7 WHERE id = $8"

    try:
        await conn.execute(
            query,
            notification.telegram_id,
            notification.truck_id,
            notification.notification_type_id,
            notification.every_minutes,
            notification.last_send_time,
            notification.warning_type,
            notification.engine_status,
            notification.id
        )
    except Exception as ex:
        logger.error(f"Error with updating notification: {ex}")
    finally:
        await conn.close()