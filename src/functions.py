from config import ADMIN_ID

async def is_admin(user_id) -> bool:
    return user_id == ADMIN_ID