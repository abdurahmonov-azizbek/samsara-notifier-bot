import db
from models import User
from logger import logger
import constants

async def get_all():
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.USER_TABLE}"
    try:
        rows = await conn.fetch(query)
        users = [
            User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                full_name=row['full_name'],
                company_id=row['company_id'],
                balance=row['balance']
            )
            for row in rows
        ]
        return users
    except Exception as ex:
        logger.error(f"Error fetching all users: {ex}")
        return []
    finally:
        await conn.close()

async def get_by_id(id: int, id_column: str | None = "id"):
    conn = await db.get_db_connection()
    query = f"SELECT * FROM {constants.USER_TABLE} WHERE {id_column} = $1"

    try:
        row = await conn.fetchrow(query, id)
        if not row:
            logger.info(f"No user found with id: {id}")
            return None

        user = User(
            id=row['id'],
            telegram_id=row['telegram_id'],
            full_name=row['full_name'],
            company_id=row['company_id'],
            balance=row['balance']
        )

        return user
    except Exception as ex:
        logger.error(f"Error fetching user by id: {ex}")
        return None
    finally:
        await conn.close()

async def create(user: User):
    conn = await db.get_db_connection()
    query = f"INSERT INTO {constants.USER_TABLE}(telegram_id, full_name, company_id, balance) VALUES ($1, $2, $3, $4)"

    try:
        await conn.execute(
            query,
            user.telegram_id,
            user.full_name,
            user.company_id,
            user.balance
        )
    except Exception as ex:
        logger.error(f"Eror with creating user: {ex}")
    finally:
        await conn.close()  

async def update(user: User):
    conn = await db.get_db_connection()
    query = f"UPDATE {constants.USER_TABLE} SET telegram_id = $1, full_name = $2, company_id = $3, balance = $4 WHERE id = $5"

    try:
        await conn.execute(
            query,
            user.telegram_id,
            user.full_name,
            user.company_id,
            user.balance,
            user.id
        )
    except Exception as ex:
        logger.error(f"Error with updating user: {ex}")
    finally:
        await conn.close()

async def delete_by_id(id: int, id_column: str | None = "id"):
    conn = await db.get_db_connection()
    query = f"DELETE FROM {constants.USER_TABLE} WHERE {id_column} = $1"

    try:
        await conn.execute(query, id)
        logger.info(f"Deleted row where {id_column} = {id}")
    except Exception as e:
        logger.error(f"Error while deleting user by id: {e}")
    finally:
        await conn.close()