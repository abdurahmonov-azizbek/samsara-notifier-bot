from operator import truediv

from src.models import  TruckLocation
from src import db
from src import constants
from src.logger import  logger
from typing import List, Optional

async def get_all() -> List[TruckLocation]:
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.TRUCK_LOCATION_TABLE}"

    try:
        rows = await conn.fetch(query)
        truck_locations = [
            TruckLocation(
                id=row['id'],
                truck_id=row['truck_id'],
                location=row['location']
            )
            for row in rows]

        return truck_locations
    except Exception as e:
        logger.error("Error while fetching all truck locations")
    finally:
        await conn.close()

async def get_by_id(id: int, id_column: str = "id") -> TruckLocation:
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.TRUCK_LOCATION_TABLE} WHERE {id_column} = $1"

    try:
        row = await conn.fetchrow(query, id)
        truck_location = TruckLocation(
            id=row['id'],
            truck_id=row['truck_id'],
            location=row['location']
        )

        return truck_location
    except Exception as e:
        logger.error(f"Error in get by id in truck location: {e}")
    finally:
        await conn.close()

async def create(truck_location: TruckLocation):
    conn = await db.get_db_connection()
    query = f"INSERT INTO {constants.TRUCK_LOCATION_TABLE}(truck_id, location) VALUES ($1, $2)"

    try:
        await conn.execute(
            query,
            truck_location.truck_id,
            truck_location.location
        )

        return True
    except Exception as e:
        logger.error(f"Error in create in truck location: {e}")
    finally:
        await conn.close()


async def update(truck_location: TruckLocation):
    conn = await db.get_db_connection()
    query = f"UPDATE {constants.TRUCK_LOCATION_TABLE} SET truck_id = $1, location = $2 WHERE id = $3"

    try:
        await conn.execute(
            query,
            truck_location.truck_id,
            truck_location.location,
            truck_location.id
        )

        return True
    except Exception as e:
        logger.error(f"Error in update in truck location: {e}")
    finally:
        await conn.close()