import asyncio
import sqlite3
import logging
import html
from telethon import TelegramClient, events, functions
from telethon.sessions import StringSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- KONFIGURATSIYA ---
BOT_TOKEN = "8506547570:AAF6WSX79RzyuTEA7e31WRP1FNG_gwgh82Y"
ADMIN_ID = 7740552653
API_ID = 30858730
API_HASH = "25106c9d80e8d8354053c1da9391edb8"
SESSION_STRING = "1ApWapzMBu7f15vvJDVKVjJAjWZRjxr1LSXGgjr0vkGbgAyoxUWS7G19u96UDdQL9woMod0NUp1I9J_rcpdNi63866eiDTLWu9kUGV-UNeQ4OMuqmVvmnh_qDxtPDQMtmBc22-cMKPXoUGeYogrCCjeiNH_LBmJwdHuh9nlw1D0qgHcq1v_lC2SHKaxpc7O32raWAtc3f5OtprBQs751qEBRh8Zo7jaYC2z6adxnIYUkG8kr6EDLyBZ5U8hBzkzgo8TCwm_0QSRDaoeiMItbQ7pNDJN7Vp5cnxsD1MZqwlNWdR_pXHNyyoL_7Eu8gJyoVTPBOPmLoetYvL8-C-eyqrTxGaUJYzaE="

PERSONAL_GROUP_ID = -1003381786521

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS keywords (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS search_groups (id INTEGER PRIMARY KEY, group_id INTEGER UNIQUE, group_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS user_state (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT)')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

# --- KLAVIATURALAR ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="➕ Kalit so'z qo'shish", callback_data='add_keyword'),
         InlineKeyboardButton(text="📋 Kalit so'zlar", callback_data='view_keywords')],
        [InlineKeyboardButton(text="🗑 Kalit so'zlarni o'chirish", callback_data='delete_keywords')],
        [InlineKeyboardButton(text="➕ Guruh qo'shish", callback_data='add_search_group'),
         InlineKeyboardButton(text="📋 Guruhlar ro'yxati", callback_data='view_search_groups')],
        [InlineKeyboardButton(text="🗑 Guruhni o'chirish", callback_data='delete_search_group')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data='back_menu')]])

# Begonalar uchun klaviatura
def guest_keyboard():
    kb = [[InlineKeyboardButton(text="👨‍💻 Adminga bog'lanish", url=f"tg://user?id={ADMIN_ID}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- USERBOT HANDLER ---
@client.on(events.NewMessage)
async def userbot_handler(event):
    try:
        search_groups = [g[0] for g in db_query("SELECT group_id FROM search_groups", fetch=True)]
        if event.chat_id not in search_groups: return

        text = event.message.message
        if not text: return

        keywords = [k[0] for k in db_query("SELECT keyword FROM keywords", fetch=True)]
        found = [kw for kw in keywords if kw.lower() in text.lower()]

        if found:
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            s_name = html.escape(f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Foydalanuvchi")
            g_name = html.escape(getattr(chat, 'title', 'Guruh'))
            msg_text = html.escape(text[:800])
            user_id = sender.id

            report = (
                f"🔍 <b>Kalit so'z topildi:</b> {', '.join(found)}\n"
                f"<b>📍 Guruh:</b> {g_name}\n"
                f"<b>👤 Foydalanuvchi:</b> {s_name}\n"
                f"<b>🆔 ID:</b> <code>{user_id}</code>\n\n"
                f"<b>📝 Xabar:</b>\n<i>{msg_text}</i>"
            )

            # Profilga o'tish tugmasi
            p_url = f"https://t.me/{sender.username}" if sender.username else f"tg://user?id={user_id}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profilga o'tish", url=p_url)]])

            await bot.send_message(chat_id=PERSONAL_GROUP_ID, text=report, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Xatolik userbot_handler: {e}")

# --- BOT HANDLERLARI ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"👋 Salom Admin!\n🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
    else:
        # Begona foydalanuvchilar uchun
        await message.answer(
            "👋 Salom!\n\n⚠️ <b>Ushbu botdan faqat adminlar foydalana oladi.</b>\n"
            "Botga kirish ruxsatnomasi yo'q.",
            reply_markup=guest_keyboard(),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    db_query("DELETE FROM user_state WHERE user_id=?", (callback.from_user.id,))
    await callback.message.edit_text("🤖 <b>Admin paneli:</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "add_keyword")
async def add_keyword_call(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, 'waiting_keyword', ''))
    await callback.message.edit_text("📝 <b>Kalit so'z kiriting:</b>", reply_markup=back_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "view_keywords")
async def view_keywords(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    kws = db_query("SELECT keyword FROM keywords", fetch=True)
    text = "📋 <b>Kalit so'zlar:</b>\n\n" + ("\n".join([f"• {html.escape(k[0])}" for k in kws]) if kws else "Bo'sh")
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "delete_keywords")
async def delete_keywords_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    kws = db_query("SELECT keyword FROM keywords", fetch=True)
    if not kws: return await callback.answer("Bo'sh")
    kb = [[InlineKeyboardButton(text=f"❌ {k[0]}", callback_data=f"delkw_{k[0]}")] for k in kws]
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_menu")])
    await callback.message.edit_text("🗑 <b>O'chirish:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("delkw_"))
async def del_keyword(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    kw = callback.data.split("_", 1)[1]
    db_query("DELETE FROM keywords WHERE keyword=?", (kw,))
    await delete_keywords_menu(callback)

@dp.callback_query(F.data == "add_search_group")
async def add_group_call(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, 'waiting_group', ''))
    await callback.message.edit_text("📝 <b>Guruh linkini yuboring:</b>", reply_markup=back_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "view_search_groups")
async def view_groups(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    gps = db_query("SELECT group_name, group_id FROM search_groups", fetch=True)
    text = "📋 <b>Guruhlar:</b>\n\n" + ("\n".join([f"• {html.escape(g[0])}" for g in gps]) if gps else "Bo'sh")
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "delete_search_group")
async def delete_group_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    gps = db_query("SELECT group_name, group_id FROM search_groups", fetch=True)
    if not gps: return await callback.answer("Bo'sh")
    kb = [[InlineKeyboardButton(text=f"🗑 {g[0]}", callback_data=f"delgp_{g[1]}")] for g in gps]
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_menu")])
    await callback.message.edit_text("🗑 <b>O'chirish:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("delgp_"))
async def del_group(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    gid = int(callback.data.split("_")[1])
    db_query("DELETE FROM search_groups WHERE group_id=?", (gid,))
    await delete_group_menu(callback)

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    state_data = db_query("SELECT state FROM user_state WHERE user_id=?", (message.from_user.id,), fetch=True)
    if not state_data: return
    state = state_data[0][0]

    if state == 'waiting_keyword':
        db_query("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (message.text.strip(),))
        await message.answer("✅ Qo'shildi", reply_markup=main_menu_keyboard())
        db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))
    elif state == 'waiting_group':
        try:
            entity = await client.get_entity(message.text.strip())
            await client(functions.channels.JoinChannelRequest(channel=entity))
            db_query("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", (entity.id if str(entity.id).startswith("-100") else int(f"-100{entity.id}"), entity.title))
            await message.answer("✅ Guruh qo'shildi", reply_markup=main_menu_keyboard())
            db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))
        except Exception as e:
            await message.answer(f"❌ Xato: {e}", reply_markup=back_keyboard())

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    await client.start()
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    asyncio.run(main())
