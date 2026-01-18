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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- DATABASE ---
def init_db():
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS keywords (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE)')
        c.execute('CREATE TABLE IF NOT EXISTS search_groups (id INTEGER PRIMARY KEY, group_id INTEGER UNIQUE, group_name TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS user_state (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT)')
        conn.commit()

def db_query(query, params=(), fetch=False):
    with sqlite3.connect('bot_data.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        res = c.fetchall() if fetch else None
        conn.commit()
        return res

# --- KEYBOARDS ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Kalit so'zlar", callback_data='keyword_menu')],
        [InlineKeyboardButton(text="📡 Izlovchi guruhlar", callback_data='search_group_menu')],
        [InlineKeyboardButton(text="📢 Shaxsiy guruh", callback_data='personal_group_menu')]
    ])

def sub_menu(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data=f'add_{prefix}')],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data=f'view_{prefix}')],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f'del_menu_{prefix}')],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data='back_main')]
    ])

def cancel_btn(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Bekor qilish", callback_data=f'{prefix}_menu')]])

# --- USERBOT HANDLER ---
@client.on(events.NewMessage)
async def handle_new_message(event):
    try:
        s_groups = [g[0] for g in db_query("SELECT group_id FROM search_groups", fetch=True)]
        if event.chat_id not in s_groups: return

        keywords = [k[0] for k in db_query("SELECT keyword FROM keywords", fetch=True)]
        text = event.message.message
        if not text: return
        
        found = [kw for kw in keywords if kw.lower() in text.lower()]
        if found:
            res = db_query("SELECT value FROM settings WHERE key='personal_group_id'", fetch=True)
            if not res: return
            
            sender = await event.get_sender()
            s_name = html.escape(f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "User")
            p_url = f"https://t.me/{sender.username}" if sender.username else f"tg://user?id={sender.id}"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profilga o'tish", url=p_url)]])
            report = f"🔍 <b>Topildi:</b> {', '.join(found)}\n<b>👤 User:</b> {s_name}\n\n<b>📝 Xabar:</b>\n<i>{html.escape(text[:800])}</i>"
            await bot.send_message(chat_id=int(res[0][0]), text=report, reply_markup=kb, parse_mode="HTML")
    except: pass

# --- BOT COMMANDS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    db_query("DELETE FROM user_state WHERE user_id=?", (callback.from_user.id,))
    await callback.message.edit_text("🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_menu(), parse_mode="HTML")

# --- MENUS ---
@dp.callback_query(F.data.in_({"keyword_menu", "search_group_menu", "personal_group_menu"}))
async def show_menus(callback: types.CallbackQuery):
    prefix = callback.data.replace("_menu", "")
    titles = {"keyword": "🔑 Kalit so'zlar", "search_group": "📡 Izlovchi guruhlar", "personal_group": "📢 Shaxsiy guruh"}
    await callback.message.edit_text(f"<b>{titles[prefix]} boshqaruvi:</b>", reply_markup=sub_menu(prefix), parse_mode="HTML")

# --- ADD ACTIONS ---
@dp.callback_query(F.data.startswith("add_"))
async def add_start(callback: types.CallbackQuery):
    prefix = callback.data.replace("add_", "")
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, f"wait_{prefix}", ""))
    txt = "📝 Kalit so'zlarni vergul bilan yuboring (max 1000):" if prefix == "keyword" else "📡 Link yoki ID yuboring:"
    await callback.message.edit_text(txt, reply_markup=cancel_btn(prefix))

# --- VIEW ACTIONS ---
@dp.callback_query(F.data.startswith("view_"))
async def view_list(callback: types.CallbackQuery):
    prefix = callback.data.replace("view_", "")
    if prefix == "keyword":
        data = db_query("SELECT keyword FROM keywords", fetch=True)
        txt = "📋 <b>So'zlar:</b>\n\n" + ("\n".join([f"• {k[0]}" for k in data]) if data else "Bo'sh")
    elif prefix == "search_group":
        data = db_query("SELECT group_name FROM search_groups", fetch=True)
        txt = "📋 <b>Guruhlar:</b>\n\n" + ("\n".join([f"• {g[0]}" for g in data]) if data else "Bo'sh")
    else:
        res = db_query("SELECT value FROM settings WHERE key='personal_group_id'", fetch=True)
        txt = f"📢 <b>Shaxsiy guruh ID:</b> <code>{res[0][0]}</code>" if res else "O'rnatilmagan"
    await callback.message.edit_text(txt, reply_markup=sub_menu(prefix), parse_mode="HTML")

# --- DELETE MENUS ---
@dp.callback_query(F.data.startswith("del_menu_"))
async def delete_menu(callback: types.CallbackQuery):
    prefix = callback.data.replace("del_menu_", "")
    if prefix == "personal_group":
        db_query("DELETE FROM settings WHERE key='personal_group_id'")
        return await callback.answer("🗑 O'chirildi", show_alert=True) or await show_menus(callback)
    
    table = "keywords" if prefix == "keyword" else "search_groups"
    col = "keyword" if prefix == "keyword" else "group_name, group_id"
    data = db_query(f"SELECT {col} FROM {table}", fetch=True)
    
    if not data: return await callback.answer("Ro'yxat bo'sh", show_alert=True)
    
    kb = []
    for item in data:
        if prefix == "keyword":
            kb.append([InlineKeyboardButton(text=f"❌ {item[0]}", callback_data=f"rm_kw_{item[0]}")])
        else:
            kb.append([InlineKeyboardButton(text=f"🗑 {item[0]}", callback_data=f"rm_sg_{item[1]}")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"{prefix}_menu")])
    await callback.message.edit_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith(("rm_kw_", "rm_sg_")))
async def delete_action(callback: types.CallbackQuery):
    if callback.data.startswith("rm_kw_"):
        db_query("DELETE FROM keywords WHERE keyword=?", (callback.data[6:],))
        prefix = "keyword"
    else:
        db_query("DELETE FROM search_groups WHERE group_id=?", (callback.data[6:],))
        prefix = "search_group"
    await delete_menu(callback)

# --- INPUT HANDLER ---
@dp.message(F.text)
async def handle_input(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    state_res = db_query("SELECT state FROM user_state WHERE user_id=?", (message.from_user.id,), fetch=True)
    if not state_res: return
    state = state_res[0][0]

    try:
        if state == "wait_keyword":
            kws = [k.strip() for k in message.text.split(",") if k.strip()][:1000]
            for k in kws: db_query("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (k,))
            await message.answer(f"✅ {len(kws)} ta so'z qo'shildi", reply_markup=sub_menu("keyword"))
            db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))
        
        elif state in ["wait_search_group", "wait_personal_group"]:
            entity = await client.get_entity(message.text.strip())
            eid = entity.id if str(entity.id).startswith("-100") else int(f"-100{entity.id}")
            
            if state == "wait_search_group":
                await client(functions.channels.JoinChannelRequest(channel=entity))
                db_query("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", (eid, entity.title))
                await message.answer(f"✅ {entity.title} qo'shildi", reply_markup=sub_menu("search_group"))
            else:
                db_query("REPLACE INTO settings (key, value) VALUES ('personal_group_id', ?)", (str(eid),))
                await message.answer(f"✅ Shaxsiy guruh: {entity.title}", reply_markup=sub_menu("personal_group"))
            db_query("DELETE FROM user_state WHERE user_id=?", (message.from_user.id,))
            
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}\n\nQayta urinib ko'ring:")

# --- START ---
async def main():
    init_db()
    await client.start()
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    asyncio.run(main())
