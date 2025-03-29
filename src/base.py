from aiogram import Bot, Dispatcher
from src import  config

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()