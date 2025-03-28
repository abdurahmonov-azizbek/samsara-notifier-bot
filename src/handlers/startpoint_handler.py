from aiogram import Router, F
from aiogram.types import *
from aiogram.filters import Command
from services import user_service
from logger import logger
import constants
import functions as fn
import keyboards

router = Router()


@router.message(Command("start"))
async def welcome(message: Message):
    try:
        user_id = message.from_user.id
        if await fn.is_admin(user_id):
            await message.answer("👮‍♂️You are admin!\n\n\tWelcome to admin menu", reply_markup=keyboards.admin_menu)
            return
        
        user = await user_service.get_by_id(user_id, constants.TELEGRAM_ID)
        if not user:
            await message.answer("You have no access for using this bot!", reply_markup=ReplyKeyboardRemove())
            return

        await message.answer("👋 Hi.\n\nWelcome to our bot", reply_markup=keyboards.user_menu)


    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply(constants.ERROR_MESSAGE)