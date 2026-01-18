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
        [InlineKeyboardButton(text="🔑 Kalit so'zlar", callback_data='keyword_menu')],
        [InlineKeyboardButton(text="📡 Izlovchi guruhlar", callback_data='search_group_menu')],
        [InlineKeyboardButton(text="📢 Shaxsiy guruh", callback_data='personal_group_menu')]
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

def cancel_keyboard(back_to):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Bekor qilish", callback_data=back_to)]])

# --- USERBOT LOGIKASI ---
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
            s_name = html.escape(f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Foydalanuvchi")
            p_url = f"https://t.me/{sender.username}" if sender.username else f"tg://user?id={sender.id}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profilga o'tish", url=p_url)]])
            
            report = f"🔍 <b>Topildi:</b> {', '.join(found)}\n<b>👤 Foydalanuvchi:</b> {s_name}\n\n<b>📝 Xabar:</b>\n<i>{html.escape(text[:800])}</i>"
            await bot.send_message(chat_id=p_group_id, text=report, reply_markup=kb, parse_mode="HTML")
    except: pass

# --- BOT HANDLERLARI ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🤖 <b>Asosiy boshqaruv menyusi:</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "back_menu")
async def back_to_main(callback: types.CallbackQuery):
    db_query("DELETE FROM user_state WHERE user_id=?", (callback.from_user.id,))
    await callback.message.edit_text("🤖 <b>Asosiy boshqaruv menyusi:</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data.in_({"keyword_menu", "search_group_menu", "personal_group_menu"}))
async def section_menus(callback: types.CallbackQuery):
    prefix = callback.data.replace("_menu", "")
    titles = {"keyword": "🔑 Kalit so'zlar", "search_group": "📡 Izlovchi guruhlar", "personal_group": "📢 Shaxsiy guruh"}
    await callback.message.edit_text(f"<b>{titles[prefix]} bo'limi:</b>", reply_markup=sub_menu_keyboard(prefix), parse_mode="HTML")

# --- QO'SHISH AMALLARI ---
@dp.callback_query(F.data.startswith("add_"))
async def add_actions(callback: types.CallbackQuery):
    prefix = callback.data.replace("add_", "")
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, f"wait_{prefix}", ''))
    
    msgs = {
        "keyword": "📝 Kalit so'zlarni yuboring.\n(Bir nechta bo'lsa vergul bilan ajrating, max 1000 ta):",
        "search_group": "📡 Kuzatiladigan guruh linkini yoki ID-sini yuboring:",
        "personal_group": "📢 Natijalar boradigan shaxsiy guruh linkini yoki ID-sini yuboring:"
    }
    await callback.message.edit_text(msgs[prefix], reply_markup=cancel_keyboard(f"{prefix}_menu"))

# --- KO'RISH VA O'CHIRISH (Oldingi mantiq saqlangan) ---
@dp.callback_query(F.data == "view_keyword")
async def v_kw(c: types.CallbackQuery):
    data = db_query("SELECT keyword FROM keywords", fetch=True)
    res = "\n".join([f"• {html.escape(k[0])}" for k in data]) if data else "Bo'sh."
    await c.message.edit_text(f"📋 <b>Ro'yxat:</b>\n\n{res}", reply_markup=sub_menu_keyboard("keyword"), parse_mode="HTML")

@dp.callback_query(F.data == "view_search_group")
async def v_sg(c: types.CallbackQuery):
    data = db_query("SELECT group_name FROM search_groups", fetch=True)
    res = "\n".join([f"• {html.escape(g[0])}" for g in data]) if data else "Bo'sh."
    await c.message.edit_text(f"📋 <b>Guruhlar:</b>\n\n{res}", reply_markup=sub_menu_keyboard("search_group"), parse_mode="HTML")

@dp.callback_query(F.data == "view_personal_group")
async def v_pg(c: types.CallbackQuery):
    res = db_query("SELECT value FROM settings WHERE key='personal_group_id'", fetch=True)
    txt = f"🆔 ID: <code>{res[0][0]}</code>" if res else "O'rnatilmagan."
    await c.message.edit_text(f"📋 <b>Shaxsiy guruh:</b>\n{txt}", reply_markup=sub_menu_keyboard("personal_group"), parse_mode="HTML")

# --- TEXT HANDLER (XATOLIKLARNI TEKSHIRISH BILAN) ---
@dp.message(F.text)
async def handle_admin_inputs(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    state_row = db_query("SELECT state FROM user_state WHERE user_id=?", (message.from_user.id,), fetch=True)
    if not state_row: return
    state = state_row[0][0]

    if state == 'wait_keyword':
        # Vergul bilan ajratish (max 1000 ta)
        raw_keywords = [k.strip() for k in message.text.split(",") if k.strip()][:1000]
        if not raw_keywords:
            return await message.answer("❌ Hech qanday so'z topilmadi. Qayta yuboring:")
        
        for kw in raw_keywords:
            db_query("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (kw,))
        
        await message.answer(f"✅ {len(raw_keywords)} ta kalit so'z saqlandi.", reply_markup=sub_menu_keyboard("keyword"))
        db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))

    elif state in ['wait_search_group', 'wait_pg']:
        try:
            target = message.text.strip()
            entity = await client.get_entity(target)
            p_id = entity.id if str(entity.id).startswith("-100") else int(f"-100{entity.id}")
            
            if state == 'wait_search_group':
                await client(functions.channels.JoinChannelRequest(channel=entity))
                db_query("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", (p_id, entity.title))
                await message.answer(f"✅ {entity.title} qo'shildi.", reply_markup=sub_menu_keyboard("search_group"))
            else:
                db_query("REPLACE INTO settings (key, value) VALUES ('personal_group_id', ?)", (str(p_id),))
                await message.answer(f"✅ Shaxsiy guruh o'rnatildi: {entity.title}", reply_markup=sub_menu_keyboard("personal_group"))
            
            db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))
        except Exception as e:
            # Xatolik bo'lsa state o'chmaydi, bot qayta so'raydi
            await message.answer(f"❌ Xato yuz berdi: {str(e)}\n\nQayta urinib ko'ring yoki linkni tekshiring:")

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    await client.start()
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    asyncio.run(main())
