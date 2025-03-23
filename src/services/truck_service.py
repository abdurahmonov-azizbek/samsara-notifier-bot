from typing import Union, Optional

from logger import logger

from src import constants, db
from src.models import Truck


async def get_all() -> list[Truck]:
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.TRUCK_TABLE}"
    try:
        rows = await conn.fetch(query)
        trucks = [
            Truck(
                id=row['id'],
                name=row['name'],
                truck_id=row['truck_id'],
                company_id=row['company_id']
            )
            for row in rows
        ]
        return trucks
    except Exception as ex:
        logger.error(f"Error fetching all trucks: {ex}")
        return []
    finally:
        await conn.close()


async def get_by_company_id(companyId) -> list[Truck]:
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.TRUCK_TABLE} WHERE company_id = $1"
    try:
        rows = await conn.fetch(query, companyId)
        trucks = [
            Truck(
                id=row['id'],
                name=row['name'],
                truck_id=row['truck_id'],
                company_id=row['company_id']
            )
            for row in rows
        ]
        return trucks
    except Exception as ex:
        logger.error(f"Error fetching all trucks: {ex}")
        return []
    finally:
        await conn.close()


async def get_by_id(id: int, id_column: Union[str, None] = "id") -> Union[Truck, None]:
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.TRUCK_TABLE} WHERE {id_column} = $1"
    try:
        row = await conn.fetchrow(query, id)
        if not row:
            logger.info(f"No truck found with {id_column}: {id}")
            return None

        truck = Truck(
            id=row['id'],
            name=row['name'],
            truck_id=row['truck_id'],
            company_id=row['company_id']
        )
        return truck
    except Exception as ex:
        logger.error(f"Error fetching truck by {id_column}: {ex}")
        return None
    finally:
        await conn.close()


async def create(truck: Truck):
    conn = await db.get_db_connection()
    query = f"INSERT INTO {constants.TRUCK_TABLE}(name, truck_id, company_id) VALUES ($1, $2, $3)"
    try:
        await conn.execute(
            query,
            truck.name,
            truck.truck_id,
            truck.company_id
        )
        logger.info(f"Truck created!")
    except Exception as ex:
        logger.error(f"Error creating truck: {ex}")
    finally:
        await conn.close()


async def update(truck: Truck, update_by: Optional[str] = "id"):
    conn = await db.get_db_connection()
    query = f"UPDATE {constants.TRUCK_TABLE} SET name = $1, truck_id = $2, company_id = $3 WHERE {update_by} = $4"
    try:
        await conn.execute(
            query,
            truck.name,
            truck.truck_id,
            truck.company_id,
            truck.id
        )
        logger.info(f"Truck updated with id: {truck.id}")
    except Exception as ex:
        logger.error(f"Error updating truck: {ex}")
    finally:
        await conn.close()


async def delete_by_id(id: int, id_column: Optional[str] = "id"):
    conn = await db.get_db_connection()
    query = f"DELETE FROM {constants.TRUCK_TABLE} WHERE {id_column} = $1"
    try:
        await conn.execute(query, id)
        logger.info(f"Deleted truck where {id_column} = {id}")
    except Exception as ex:
        logger.error(f"Error deleting truck by {id_column}: {ex}")
    finally:
        await conn.close()
