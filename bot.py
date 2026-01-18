import asyncio
import sqlite3
import logging
import html
import re
from telethon import TelegramClient, events, functions
from telethon.sessions import StringSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- KONFIGURATSIYA ---
BOT_TOKEN = "8137576363:AAHerJWL_b4kgQsTY03_Dt6sLuPny-BlZ8g"
ADMIN_LIST = [7664337104, 7740552653] 
DEV_ID = 7740552653
API_ID = 31654640
API_HASH = "22e66db2dba07587217d2f308ae412fb"
SESSION_STRING = "1ApWapzMBu4E9Kp6_zhIWbAr9GndIqukjWw51smf1l9CXbEviZSSGZCg3RzqIS4HCEigBsBvup0b6iPctHFcigaO_p70kKhrJ2Qkza5Ua2bqcJbFIlRZtJPxfoESMmXMqEtZWQ-VytgJp4sQFT_6sta_LMldT6wiCai5wMPKO51iKHYUYHB2ggRRr7Lp9JOprTRmBWdOVYX0povfDgWDrIgBuO1BVXhTpBin2BpjwxvdknZkzv-wiZJRpAMuXfazNM1cg80ggNbNP313yY3ptY7jBR_TjM1--LbzSzTY9IpC5RPwcg-OQB1nixO3U-KP4e4LhLrGi0i4F2y-R3QagopY8DelDotI="
PERSONAL_GROUP_ID = -1003267783623

logging.basicConfig(level=logging.ERROR)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- DB OPERATSIYALARI (MULTI-ADMIN UCHUN OPTIMALLASHGAN) ---
def db_op(query, params=(), fetch=False):
    # check_same_thread=False va timeout orqali qotishlar oldi olingan
    with sqlite3.connect('bot_data.db', timeout=30, check_same_thread=False) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        conn.commit()
    return None

def init_db():
    db_op('CREATE TABLE IF NOT EXISTS keywords (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE)')
    db_op('CREATE TABLE IF NOT EXISTS search_groups (id INTEGER PRIMARY KEY, group_id INTEGER UNIQUE, group_name TEXT)')
    db_op('CREATE TABLE IF NOT EXISTS user_state (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT)')

# --- ASOSIY MENYU ---
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Kalit so'zlar", callback_data='open_keywords')],
        [InlineKeyboardButton(text="📡 Izlovchi guruhlar", callback_data='open_groups')],
        [InlineKeyboardButton(text="⚙️ Tizim holati", callback_data='sys_status')]
    ])

# --- SUB MENYULAR (PREFIX FARQLANGAN) ---
def sub_kb(mode):
    # mode faqat 'kw' yoki 'gr' bo'lishi mumkin
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data=f'add_new_{mode}')],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data=f'view_all_{mode}')],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f'list_del_{mode}')],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data='main_home')]
    ])

# --- USERBOT ---
@client.on(events.NewMessage)
async def watcher(event):
    try:
        groups = [g[0] for g in db_op("SELECT group_id FROM search_groups", fetch=True)]
        if event.chat_id not in groups: return
        
        words = [k[0] for k in db_op("SELECT keyword FROM keywords", fetch=True)]
        text = event.message.message
        if not text: return
        
        found = [w for w in words if w.lower() in text.lower()]
        if found:
            sender = await event.get_sender()
            chat = await event.get_chat()
            p_link = f"https://t.me/{sender.username}" if getattr(sender, 'username', None) else f"tg://user?id={sender.id}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profil", url=p_link)]])
            msg = (f"🔍 <b>Topildi:</b> {', '.join(found)}\n"
                   f"<b>📍 Guruh:</b> {html.escape(getattr(chat, 'title', 'Guruh'))}\n\n"
                   f"<b>📝 Xabar:</b>\n<i>{html.escape(text[:800])}</i>")
            await bot.send_message(PERSONAL_GROUP_ID, msg, reply_markup=kb, parse_mode="HTML")
    except: pass

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(m: types.Message):
    if m.from_user.id in ADMIN_LIST:
        await m.answer("🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "main_home")
async def go_home(c: types.CallbackQuery):
    db_op("DELETE FROM user_state WHERE user_id=?", (c.from_user.id,))
    await c.message.edit_text("🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_kb(), parse_mode="HTML")

@dp.callback_query(F.data.in_({"open_keywords", "open_groups"}))
async def sub_menu_handler(c: types.CallbackQuery):
    mode = "kw" if c.data == "open_keywords" else "gr"
    title = "🔑 Kalit so'zlar" if mode == "kw" else "📡 Izlovchi guruhlar"
    await c.message.edit_text(f"<b>{title} bo'limi:</b>", reply_markup=sub_kb(mode), parse_mode="HTML")

# --- O'CHIRISH (XATOLIK TUZATILGAN JOY) ---
@dp.callback_query(F.data.startswith("list_del_"))
async def del_list(c: types.CallbackQuery, force_mode=None):
    mode = force_mode if force_mode else c.data.split("_")[2]
    
    if mode == "kw":
        data = db_op("SELECT id, keyword FROM keywords", fetch=True)
        txt = "🗑 <b>Kalit so'zni tanlang:</b>"
    else:
        data = db_op("SELECT id, group_name FROM search_groups", fetch=True)
        txt = "🗑 <b>Guruhni tanlang:</b>"

    kb_list = []
    for item in data:
        # Callback ma'lumotlari qat'iy ajratildi: do_del_kw_ID yoki do_del_gr_ID
        kb_list.append([InlineKeyboardButton(text=f"❌ {item[1]}", callback_data=f"do_del_{mode}_{item[0]}")])
    
    kb_list.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f'open_{"keywords" if mode=="kw" else "groups"}')])
    await c.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list), parse_mode="HTML")

@dp.callback_query(F.data.startswith("do_del_"))
async def delete_action(c: types.CallbackQuery):
    parts = c.data.split("_")
    mode = parts[2] # kw yoki gr
    idx = parts[3] # ID

    if mode == "kw":
        db_op("DELETE FROM keywords WHERE id=?", (idx,))
        await c.answer("✅ Kalit so'z o'chirildi")
    else:
        res = db_op("SELECT group_id FROM search_groups WHERE id=?", (idx,), fetch=True)
        if res:
            try: await client(functions.channels.LeaveChannelRequest(channel=res[0][0]))
            except: pass
        db_op("DELETE FROM search_groups WHERE id=?", (idx,))
        await c.answer("✅ Guruh o'chirildi")
    
    # MUHIM: O'chirilgandan keyin o'sha mode'da qolish
    await del_list(c, force_mode=mode)

# --- QO'SHISH (KETMA-KETLIK VA YAKUNLASH) ---
@dp.callback_query(F.data.startswith("add_new_"))
async def start_add(c: types.CallbackQuery):
    mode = c.data.split("_")[2]
    db_op("REPLACE INTO user_state VALUES (?, ?, ?)", (c.from_user.id, f"wait_{mode}", ""))
    
    txt = "📝 Kalit so'zlarni yuboring (vergul bilan yoki bittalab):" if mode == "kw" else \
          "📡 Guruh linkini yuboring (Masalan: @guruh):"
    
    await c.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Yakunlash", callback_data=f'open_{"keywords" if mode=="kw" else "groups"}')]
    ]))

@dp.message(F.text)
async def text_handler(m: types.Message):
    if m.from_user.id not in ADMIN_LIST: return
    state = db_op("SELECT state FROM user_state WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not state: return
    
    st = state[0][0]
    if st == "wait_kw":
        ws = [w.strip() for w in m.text.split(",") if w.strip()]
        for w in ws: db_op("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (w,))
        await m.answer(f"✅ {len(ws)} ta so'z qo'shildi. Yana yuboring yoki 'Yakunlash'ni bosing.",
                       reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Yakunlash", callback_data='open_keywords')]]))
    
    elif st == "wait_gr":
        links = re.findall(r'(?:https?://)?t\.me/[a-zA-Z0-9_]{4,}|@[a-zA-Z0-9_]{4,}', m.text)
        if not links: return await m.answer("❌ Havola xato.")
        
        status = await m.answer("⏳ Ulanmoqda...")
        ok = 0
        for l in links:
            try:
                clean = re.sub(r'/\d+$', '', l.strip().replace("https://t.me/", "").replace("@", ""))
                ent = await client.get_entity(clean)
                await client(functions.channels.JoinChannelRequest(channel=ent))
                gid = ent.id if str(ent.id).startswith("-100") else int(f"-100{ent.id}")
                db_op("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", (gid, ent.title))
                ok += 1
                await asyncio.sleep(1)
            except: pass
            
        await status.edit_text(f"✅ {ok} ta guruh ulandi.\nKeyingisini yuboring yoki 'Yakunlash'ni bosing:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Yakunlash", callback_data='open_groups')]]))

# --- KO'RISH VA STATUS ---
@dp.callback_query(F.data.startswith("view_all_"))
async def show_list(c: types.CallbackQuery):
    mode = c.data.split("_")[2]
    table = "keywords" if mode == "kw" else "search_groups"
    col = "keyword" if mode == "kw" else "group_name"
    data = db_op(f"SELECT {col} FROM {table}", fetch=True)
    txt = f"📋 <b>Ro'yxat:</b>\n\n" + ("\n".join([f"• {k[0]}" for k in data]) if data else "Bo'sh")
    await c.message.edit_text(txt[:4000], reply_markup=sub_kb(mode), parse_mode="HTML")

@dp.callback_query(F.data == "sys_status")
async def sys_status(c: types.CallbackQuery):
    try:
        me = await client.get_me()
        k = db_op("SELECT COUNT(*) FROM keywords", fetch=True)[0][0]
        g = db_op("SELECT COUNT(*) FROM search_groups", fetch=True)[0][0]
        txt = f"⚙️ <b>Tizim:</b>\n👤 Userbot: @{me.username}\n🔑 So'zlar: {k}\n📡 Guruhlar: {g}"
        await c.message.edit_text(txt, reply_markup=main_kb(), parse_mode="HTML")
    except: await c.answer("Userbot o'chiq!")

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await client.start()
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    try: asyncio.run(main())
    except: pass
