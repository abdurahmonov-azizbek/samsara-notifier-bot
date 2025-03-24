from src import db


async def get_notification_type_id(event_type: str) -> int:
    conn = await db.get_db_connection()
    warning_events = ['SevereSpeedingEnded', 'SevereSpeedingStarted', 'PredictiveMaintenanceAlert',
                      'SuddenFuelLevelDrop',
                      'SuddenFuelLevelRise', 'GatewayUnplugged']
    engine_events = []

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


async def get_telegram_ids(vehicle_id: str, type_id: int) -> list:
    conn = await db.get_db_connection()

    query = """
        SELECT n.telegram_id, t.name AS truck_name
        FROM notification n
        JOIN truck t ON n.truck_id = t.truck_id
        WHERE n.truck_id = $1 AND n.notification_type_id = $2
    """
    rows = await conn.fetch(query, int(vehicle_id), type_id)
    return [(row["telegram_id"], row["truck_name"]) for row in rows]
