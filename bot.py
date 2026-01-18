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
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
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
        [InlineKeyboardButton(text="🔑 Kalit so'zlar boshqaruvi", callback_data='keyword_menu')],
        [InlineKeyboardButton(text="📡 Izlovchi guruhlar boshqaruvi", callback_data='search_group_menu')],
        [InlineKeyboardButton(text="📢 Shaxsiy guruh boshqaruvi", callback_data='personal_group_menu')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def sub_menu_keyboard(prefix):
    keyboard = [
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data=f'add_{prefix}')],
        [InlineKeyboardButton(text="📋 Ro'yxatni ko'rish", callback_data=f'view_{prefix}')],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f'delete_{prefix}_menu')],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data='back_menu')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Bekor qilish", callback_data='back_menu')]])

# --- USERBOT HANDLER ---
@client.on(events.NewMessage)
async def userbot_handler(event):
    try:
        res = db_query("SELECT value FROM settings WHERE key='personal_group_id'", fetch=True)
        if not res: return 
        p_group_id = int(res[0][0])

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
            
            p_url = f"https://t.me/{sender.username}" if sender.username else f"tg://user?id={sender.id}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profilga o'tish", url=p_url)]])

            report = (f"🔍 <b>Topildi:</b> {', '.join(found)}\n<b>📍 Guruh:</b> {g_name}\n"
                      f"<b>👤 Foydalanuvchi:</b> {s_name}\n\n<b>📝 Xabar:</b>\n<i>{msg_text}</i>")
            await bot.send_message(chat_id=p_group_id, text=report, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Userbot: {e}")

# --- BOT HANDLERLARI ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🤖 <b>Asosiy boshqaruv menyusi:</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👨‍💻 Bog'lanish", url=f"tg://user?id={ADMIN_ID}")]])
        await message.answer("👋 Salom! Bot faqat admin uchun.", reply_markup=kb)

@dp.callback_query(F.data == "back_menu")
async def back_to_main(callback: types.CallbackQuery):
    db_query("DELETE FROM user_state WHERE user_id=?", (callback.from_user.id,))
    await callback.message.edit_text("🤖 <b>Asosiy boshqaruv menyusi:</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")

# --- MENYU BO'LIMLARI ---
@dp.callback_query(F.data.in_({"keyword_menu", "search_group_menu", "personal_group_menu"}))
async def menus(callback: types.CallbackQuery):
    titles = {"keyword_menu": "🔑 Kalit so'zlar", "search_group_menu": "📡 Izlovchi guruhlar", "personal_group_menu": "📢 Shaxsiy guruh"}
    prefix = callback.data.replace("_menu", "")
    await callback.message.edit_text(f"<b>{titles[callback.data]} bo'limi:</b>", reply_markup=sub_menu_keyboard(prefix), parse_mode="HTML")

# --- KALIT SO'ZLAR ---
@dp.callback_query(F.data == "add_keyword")
async def add_kw(callback: types.CallbackQuery):
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, 'wait_kw', ''))
    await callback.message.edit_text("📝 Kalit so'zni yuboring:", reply_markup=back_keyboard())

@dp.callback_query(F.data == "view_keyword")
async def view_kw(callback: types.CallbackQuery):
    data = db_query("SELECT keyword FROM keywords", fetch=True)
    res = "\n".join([f"• {html.escape(k[0])}" for k in data]) if data else "Ro'yxat bo'sh."
    await callback.message.edit_text(f"📋 <b>Saqlangan kalit so'zlar:</b>\n\n{res}", reply_markup=sub_menu_keyboard("keyword"), parse_mode="HTML")

@dp.callback_query(F.data == "delete_keyword_menu")
async def del_kw_menu(callback: types.CallbackQuery):
    data = db_query("SELECT keyword FROM keywords", fetch=True)
    if not data: return await callback.answer("Ro'yxat bo'sh")
    kb = [[InlineKeyboardButton(text=f"❌ {k[0]}", callback_data=f"dkw_{k[0]}")] for k in data]
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="keyword_menu")])
    await callback.message.edit_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("dkw_"))
async def dkw_act(callback: types.CallbackQuery):
    db_query("DELETE FROM keywords WHERE keyword=?", (callback.data[4:],))
    await del_kw_menu(callback)

# --- IZLOVCHI GURUHLAR ---
@dp.callback_query(F.data == "add_search_group")
async def add_sg(callback: types.CallbackQuery):
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, 'wait_sg', ''))
    await callback.message.edit_text("📝 Guruh linkini yoki ID-sini yuboring:", reply_markup=back_keyboard())

@dp.callback_query(F.data == "view_search_group")
async def view_sg(callback: types.CallbackQuery):
    data = db_query("SELECT group_name FROM search_groups", fetch=True)
    res = "\n".join([f"• {html.escape(g[0])}" for g in data]) if data else "Guruhlar yo'q."
    await callback.message.edit_text(f"📋 <b>Kuzatilayotgan guruhlar:</b>\n\n{res}", reply_markup=sub_menu_keyboard("search_group"), parse_mode="HTML")

@dp.callback_query(F.data == "delete_search_group_menu")
async def del_sg_menu(callback: types.CallbackQuery):
    data = db_query("SELECT group_name, group_id FROM search_groups", fetch=True)
    if not data: return await callback.answer("Ro'yxat bo'sh")
    kb = [[InlineKeyboardButton(text=f"🗑 {g[0]}", callback_data=f"dsg_{g[1]}")] for g in data]
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="search_group_menu")])
    await callback.message.edit_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("dsg_"))
async def dsg_act(callback: types.CallbackQuery):
    db_query("DELETE FROM search_groups WHERE group_id=?", (callback.data[4:],))
    await del_sg_menu(callback)

# --- SHAXSIY GURUH ---
@dp.callback_query(F.data == "add_personal_group")
async def add_pg(callback: types.CallbackQuery):
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, 'wait_pg', ''))
    await callback.message.edit_text("📝 Shaxsiy guruh linki yoki ID-sini yuboring:", reply_markup=back_keyboard())

@dp.callback_query(F.data == "view_personal_group")
async def view_pg(callback: types.CallbackQuery):
    res = db_query("SELECT value FROM settings WHERE key='personal_group_id'", fetch=True)
    msg = f"🆔 ID: <code>{res[0][0]}</code>" if res else "O'rnatilmagan."
    await callback.message.edit_text(f"📋 <b>Shaxsiy guruh:</b>\n{msg}", reply_markup=sub_menu_keyboard("personal_group"), parse_mode="HTML")

@dp.callback_query(F.data == "delete_personal_group_menu")
async def del_pg(callback: types.CallbackQuery):
    db_query("DELETE FROM settings WHERE key='personal_group_id'")
    await callback.answer("O'chirildi")
    await back_to_main(callback)

# --- TEXT HANDLING ---
@dp.message(F.text)
async def text_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    state = db_query("SELECT state FROM user_state WHERE user_id=?", (message.from_user.id,), fetch=True)
    if not state: return
    cmd = state[0][0]

    try:
        if cmd == 'wait_kw':
            db_query("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (message.text.strip(),))
            await message.answer("✅ Kalit so'z qo'shildi.", reply_markup=main_menu_keyboard())
        elif cmd in ['wait_sg', 'wait_pg']:
            entity = await client.get_entity(message.text.strip())
            p_id = entity.id if str(entity.id).startswith("-100") else int(f"-100{entity.id}")
            if cmd == 'wait_sg':
                await client(functions.channels.JoinChannelRequest(channel=entity))
                db_query("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", (p_id, entity.title))
                await message.answer(f"✅ {entity.title} qo'shildi.", reply_markup=main_menu_keyboard())
            else:
                db_query("REPLACE INTO settings (key, value) VALUES ('personal_group_id', ?)", (str(p_id),))
                await message.answer(f"✅ Shaxsiy guruh o'rnatildi: {entity.title}", reply_markup=main_menu_keyboard())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))

async def main():
    init_db()
    await client.start()
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    asyncio.run(main())
