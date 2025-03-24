from typing import List

from src import constants
from src import db
from src.logger import logger
from src.models import Notification


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


async def create_status_notification(notification: Notification):
    try:
        conn = await db.get_db_connection()
        query = f"INSERT INTO {constants.NOTIFICATION_TABLE} (telegram_id, truck_id, notification_type_id, engine_status) VALUES ($1, $2, $3, $4)"

        await conn.execute(
            query,
            notification.telegram_id,
            notification.truck_id,
            2,
            notification.engine_status)

        return True
    except Exception as e:
        logger.error(f"Error while creating status notification: {e}")
    finally:
        await conn.close()


async def create_warning_notification(notification: Notification):
    try:
        conn = await db.get_db_connection()
        query = f"INSERT INTO {constants.NOTIFICATION_TABLE} (telegram_id, truck_id, notification_type_id, warning_type) VALUES ($1, $2, $3, $4)"

        await conn.execute(
            query,
            notification.telegram_id,
            notification.truck_id,
            1,
            notification.warning_type)

        return True
    except Exception as e:
        logger.error(f"Error while creating warning notification: {e}")
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


async def get_notification_type_id(event_type: str) -> int:
    conn = await db.get_db_connection()
    warning_events = ['SevereSpeedingEnded', 'SevereSpeedingStarted', 'PredictiveMaintenanceAlert',
                      'SuddenFuelLevelDrop', 'SuddenFuelLevelRise', 'GatewayUnplugged','harshEvent']
    engine_events = ['deviceMovementStopped', 'deviceMovement']

    if event_type in warning_events:
        type_name = 'Warnings'
    elif event_type in engine_events:
        type_name = 'Engine status'
    else:
        type_name = 'Warnings'

    query = """
        SELECT id FROM notification_type WHERE name = $1
    """
    type_id = await conn.fetchval(query, type_name)
    return type_id if type_id else 1


async def get_telegram_ids(vehicle_id: str, type_id: int, event_type: str) -> list:
    conn = await db.get_db_connection()

    query = """
        SELECT n.telegram_id, t.name AS truck_name
        FROM notification n
        JOIN truck t ON n.truck_id = t.truck_id
        WHERE n.truck_id = $1 AND n.notification_type_id = $2
    """
    params = [int(vehicle_id), type_id]

    if type_id == 1:
        query += " AND n.warning_type = $3"
        params.append(event_type)
    elif type_id == 2:
        query += " AND n.engine_status = $3"
        params.append(event_type)

    rows = await conn.fetch(query, *params)
    return [(row["telegram_id"], row["truck_name"]) for row in rows]
