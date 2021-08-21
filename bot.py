from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, \
                            InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from pymongo import MongoClient
import random
 
bot = Bot(token="token")
dp = Dispatcher(bot, storage=MemoryStorage())
 
cluster = MongoClient("mongodb-token")
collqueue = cluster.testdb.queue
collusers = cluster.testdb.users
collchats = cluster.testdb.chats
 
 
class SetBio(StatesGroup):
    user_bio = State()
 
 
@dp.message_handler(commands="start")
async def menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("🥑 Account"),
                KeyboardButton("☕️ Search user")
            ]
        ],
        resize_keyboard=True
    )
 
    await message.answer("🍒 Main menu", reply_markup=keyboard)
 
 
@dp.message_handler(commands=["bio", "set_bio", "new_bio", "about_me"])
async def user_bio(message: types.Message):
    if collusers.count_documents({"_id": message.from_user.id}) == 0:
        await account_user(message)
    else:
        await SetBio.user_bio.set()
        await message.answer("Please, enter a new bio")
 

@dp.message_handler(state=SetBio.user_bio)
async def process_set_bio(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["user_bio"] = message.text
        collusers.update_one({"_id": message.from_user.id}, {"$set": {"bio": data["user_bio"]}})
 
        await message.answer("You are successfully set a new bio")
        await state.finish()
 
 
@dp.message_handler(commands="account")
async def account_user(message: types.Message):
    if collusers.count_documents({"_id": message.from_user.id}) == 0:
        keyboard = ReplyKeyboardMarkup([[KeyboardButton("🍷 Registration")]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("You are not register in the system", reply_markup=keyboard)
    else:
        acc = collusers.find_one({"_id": message.from_user.id})
        text = f"""User ID: {message.from_user.id}\nBalance: {acc['balance']}\nReputation: {acc['reputation']}\nBio: {acc['bio']}"""
        keyboard = ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton("💣 Remove account"),
                    KeyboardButton("✏ Set bio"),
                    KeyboardButton("🍒 Back to menu")
                ]
            ],
            resize_keyboard=True
        )
 
        await message.answer(text, reply_markup=keyboard)
 
 
@dp.message_handler(commands=["remove", "remove_acc", "remove_account"])
async def remove_account_act(message: types.Message):
    if collusers.count_documents({"_id": message.from_user.id}) != 0:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("Yes, I agree.", callback_data=CallbackData("choice", "action").new(action="remove")),
                    InlineKeyboardButton("Cancel", callback_data=CallbackData("choice", "action").new(action="cancel"))
                ]
            ],
            one_time_keyboard=True
        )
 
        await message.answer("You are really wanna remove the account?", reply_markup=keyboard)
    else:
        await message.answer("You don't have an account")
        await menu(message)
 
 
@dp.message_handler(commands=["reg", "registration"])
async def account_registration_act(message: types.Message):
    if collusers.count_documents({"_id": message.from_user.id}) == 0:
        collusers.insert_one(
            {
                "_id": message.from_user.id,
                "balance": 0,
                "reputation": 0,
                "bio": "The unknown user of the Internet"
            }
        )
        hearts = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍"]
        await message.answer(f"{random.choice(hearts)} You are successfully registered in the system")
        await account_user(message)
    else:
        await message.answer("You already registered in the system")
        await account_user(message)
 
 
@dp.message_handler(commands=["search_user", "searchuser"])
async def search_user_act(message: types.Message):
    if message.chat.type == "private":
        if collusers.count_documents({"_id": message.from_user.id}) == 0:
            await account_user(message)
        else:
            if collchats.count_documents({"user_chat_id": message.chat.id}) != 0:
                await message.answer("You already have an active chat")
            else:
                if collqueue.count_documents({"_id": message.chat.id}) != 1:
                    keyboard = ReplyKeyboardMarkup([[KeyboardButton("📛 Stop search")]], resize_keyboard=True, one_time_keyboard=True)
                    interlocutor = collqueue.find_one({})
     
                    if interlocutor is None:
                        collqueue.insert_one({"_id": message.chat.id})
                        await message.answer("🕒 Search user began, please wait... Or you can stop searching", reply_markup=keyboard)
                    else:
                        if collqueue.count_documents({"_id": interlocutor["_id"]}) != 0:
                            collqueue.delete_one({"_id": message.chat.id})
                            collqueue.delete_one({"_id": interlocutor["_id"]})
     
                            collchats.insert_one(
                                {
                                    "user_chat_id": message.chat.id,
                                    "interlocutor_chat_id": interlocutor["_id"]
                                }
                            )
                            collchats.insert_one(
                                {
                                    "user_chat_id": interlocutor["_id"],
                                    "interlocutor_chat_id": message.chat.id
                                }
                            )
                            bio_intestlocutor = collusers.find_one({"_id": message.chat.id})["bio"]
                            bio_user = collusers.find_one({"_id": collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"]})["bio"]
                            keyboard_leave = ReplyKeyboardMarkup([[KeyboardButton("💔 Leave from chat")]], resize_keyboard=True, one_time_keyboard=True)
                            chat_info = collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"]
     
                            await message.answer(f"Interlocutor found! You can begin communicate.\nBio: {bio_user}", reply_markup=keyboard_leave)
                            await bot.send_message(text=f"Interlocutor found! You can begin communicate.\nBio: {bio_intestlocutor}", chat_id=chat_info, reply_markup=keyboard_leave)
                        else:
                            collqueue.insert_one({"_id": message.chat.id})
                            await message.answer("🕒 Search user began, please wait... Or you can stop searching", reply_markup=keyboard)
 
                else:
                    await message.answer("You already have an queue")
 
@dp.message_handler(commands=["stop_search"])
async def stop_search_act(message: types.Message):
    if collqueue.count_documents({"_id": message.chat.id}) != 0:
        collqueue.delete_one({"_id": message.chat.id})
        await menu(message)
    else:
        await message.answer("You didn't begin search an interlocutor")
 
@dp.message_handler(commands=["Yes"])
async def yes_rep_act(message: types.Message):
    if collchats.count_documents({"user_chat_id": message.chat.id}) != 0:
        collusers.update_one({"_id": message.from_user.id}, {"$inc": {"reputation": 5}})
        collchats.delete_one({"user_chat_id": message.chat.id})
        await message.answer("Ok!")
        await menu(message)
    else:
        await message.answer("You didn't begin a chat with an interlocutor")

@dp.message_handler(commands=["No"])
async def no_rep_act(message: types.Message):
    if collchats.count_documents({"user_chat_id": message.chat.id}) != 0:
        collusers.update_one({"_id": collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"]}, {"$inc": {"reputation": -5}})
        collchats.delete_one({"user_chat_id": message.chat.id})
        await message.answer("Ok!")
        await menu(message)
    else:
        await message.answer("You didn't begin a chat with an interlocutor")

@dp.message_handler(commands=["rep_menu"])
async def rep_menu(message: types.Message):
    if collchats.count_documents({"user_chat_id": message.chat.id}) != 0:
        keyboard = ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton("👍 Yes"),
                    KeyboardButton("👎 No")
                ]
            ],
            resize_keyboard=True
        )
        await message.answer("Did you enjoy the conversation with this user?", reply_markup=keyboard)
    else:
        await message.answer("You didn't begin a chat with an interlocutor")

@dp.message_handler(commands=["leave", "leave_chat"])
async def leave_from_chat_act(message: types.Message):
    if collchats.count_documents({"user_chat_id": message.chat.id}) != 0:
        await message.answer("You are left the chat")
        keyboard = ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton("👍 Yes"),
                    KeyboardButton("👎 No")
                ]
            ],
            resize_keyboard=True
        )
        await bot.send_message(text="The Interlocutor left the chat", chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"], reply_markup=keyboard)
        await bot.send_message(text="Did you enjoy the conversation with this user?", chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"], reply_markup=keyboard)
        await rep_menu(message)
    else:
        await message.answer("You didn't begin a chat with an interlocutor")
 
 
@dp.message_handler(content_types=["text", "sticker", "photo", "voice", "document"])
async def some_text(message: types.Message):
    if message.text == "🍷 Registration":
        await account_registration_act(message)
    elif message.text == "🥑 Account":
        await account_user(message)
    elif message.text == "🍒 Back to menu":
        await menu(message)
    elif message.text == "💣 Remove account":
        await remove_account_act(message)
    elif message.text == "☕️ Search user":
        await search_user_act(message)
    elif message.text == "📛 Stop search":
        await stop_search_act(message)
    elif message.text == "✏ Set bio":
        await user_bio(message)
    elif message.text == "💔 Leave from chat":
        await leave_from_chat_act(message)
    elif message.text == "👍 Yes":
        await yes_rep_act(message)
    elif message.text == "👎 No":
        await no_rep_act(message)
    elif message.content_type == "sticker":
        try:
            await bot.send_sticker(chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"], sticker=message.sticker["file_id"])
        except TypeError:
            pass
    elif message.content_type == "photo":
        try:
            await bot.send_photo(chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"], photo=message.photo[len(message.photo) - 1].file_id)
        except TypeError:
            pass
    elif message.content_type == "voice":
        try:
            await bot.send_voice(chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"], voice=message.voice["file_id"])
        except TypeError:
            pass
    elif message.content_type == "document":
        try:
            await bot.send_document(chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"], document=message.document["file_id"])
        except TypeError:
            pass
    else:
        try:
            await bot.send_message(text=message.text, chat_id=collchats.find_one({"user_chat_id": message.chat.id})["interlocutor_chat_id"])
        except TypeError:
            pass
 
 
@dp.callback_query_handler(text_contains="remove")
async def process_remove_account(callback: types.CallbackQuery):
    collusers.delete_one({"_id": callback.from_user.id})
    await callback.message.answer("You are successfully removed the account")
    await menu(callback.message)
 
 
@dp.callback_query_handler(text_contains="cancel")
async def process_cancel(callback: types.CallbackQuery):
    await callback.message.answer("Ok. Don't joke with me.")
 
if __name__ == "__main__":
    executor.start_polling(dp)