from typing import Optional, List

from src.logger import logger

from src import constants, db
from src.models import Company


async def get_all() -> list[Company]:
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.COMPANY_TABLE}"
    try:
        rows = await conn.fetch(query)
        companies = [
            Company(
                id=row['id'],
                name=row['name'],
                api_key=row['api_key']
            )
            for row in rows
        ]
        return companies
    except Exception as ex:
        logger.error(f"Error fetching all companies: {ex}")
        return []
    finally:
        await conn.close()


async def get_by_ids(ids: List[int], id_column: Optional[str] = "id") -> list[Company]:
    if not ids:
        logger.info("No IDs provided!")
        return None

    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.COMPANY_TABLE} WHERE {id_column} = ANY($1)"
    try:
        rows = await conn.fetch(query, ids)
        companies = [
            Company(
                id=row['id'],
                name=row['name'],
                api_key=row['api_key']
            )
            for row in rows
        ]
        return companies
    except Exception as ex:
        logger.error(f"Error fetching all companies: {ex}")
        return []
    finally:
        await conn.close()


async def get_by_id(id: int, id_column: Optional[str] = "id"):
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.COMPANY_TABLE} WHERE {id_column} = $1"

    try:
        row = await conn.fetchrow(query, id)
        if not row:
            logger.info(f"No company found with id: {id}")
            return None

        company = Company(
            id=row['id'],
            name=row['name'],
            api_key=row['api_key']
        )

        return company
    except Exception as ex:
        logger.error(f"Error fetching company by id: {ex}")
        return None
    finally:
        await conn.close()


async def get_by_name(name: str):
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.COMPANY_TABLE} WHERE name = $1"

    try:
        row = await conn.fetchrow(query, name)
        if not row:
            logger.info(f"No company found with name: {name}")
            return None

        company = Company(
            id=row['id'],
            name=row['name'],
            api_key=row['api_key']
        )

        return company
    except Exception as ex:
        logger.error(f"Error fetching company by id: {ex}")
        return None
    finally:
        await conn.close()


async def create(company: Company):
    conn = await db.get_db_connection()
    query = f"INSERT INTO {constants.COMPANY_TABLE}(name, api_key) VALUES ($1, $2)"

    try:
        await conn.execute(
            query,
            company.name,
            company.api_key
        )
    except Exception as ex:
        logger.error(f"Eror with creating company: {ex}")
    finally:
        await conn.close()


async def update(company: Company):
    conn = await db.get_db_connection()
    query = f"UPDATE {constants.COMPANY_TABLE} SET name = $1, api_key = $2 WHERE id = $3"

    try:
        await conn.execute(
            query,
            company.name,
            company.api_key,
            company.id
        )
        logger.info(f"Company updated with id: {company.id}")

    except Exception as ex:
        logger.error(f"Eror with updating company: {ex}")
    finally:
        await conn.close()


async def delete_by_id(id: int, id_column: Optional[str] = "id"):
    conn = await db.get_db_connection()
    query = f"DELETE FROM {constants.COMPANY_TABLE} WHERE {id_column} = $1"

    try:
        await conn.execute(query, id)
        logger.info(f"Deleted row where {id_column} = {id}")
    except Exception as e:
        logger.error(f"Error while deleting company by id: {e}")
    finally:
        await conn.close()
