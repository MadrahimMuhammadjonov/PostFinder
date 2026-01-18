import asyncio
import sqlite3
import logging
import html
import re
import os
from telethon import TelegramClient, events, functions, errors
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

# --- MA'LUMOTLAR BAZASI (QOTISHNI OLDINI OLISH UCHUN OPTIMALLASHGAN) ---
def get_db_connection():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False, timeout=20)
    conn.execute('PRAGMA journal_mode=WAL') # Multi-user rejimini yaxshilaydi
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS keywords (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS search_groups (id INTEGER PRIMARY KEY, group_id INTEGER UNIQUE, group_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS user_state (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT)')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetch=False):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(query, params)
        if fetch:
            res = c.fetchall()
            return res
        conn.commit()
    finally:
        conn.close()
    return None

# --- KLAVIATURALAR ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Kalit so'zlar", callback_data='menu_kw')],
        [InlineKeyboardButton(text="📡 Izlovchi guruhlar", callback_data='menu_gr')],
        [InlineKeyboardButton(text="⚙️ Tizim holati", callback_data='check_status')]
    ])

def sub_menu(prefix):
    # prefix: 'kw' (kalit so'z) yoki 'gr' (guruh)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data=f'add_{prefix}')],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data=f'view_{prefix}')],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f'del_list_{prefix}')],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data='back_to_main')]
    ])

# --- USERBOT LOGIKASI ---
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
            sender = await event.get_sender()
            chat = await event.get_chat()
            p_url = f"https://t.me/{sender.username}" if getattr(sender, 'username', None) else f"tg://user?id={sender.id}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profil", url=p_url)]])
            report = (f"🔍 <b>Topildi:</b> {', '.join(found)}\n"
                      f"<b>📍 Guruh:</b> {html.escape(getattr(chat, 'title', 'Guruh'))}\n\n"
                      f"<b>📝 Xabar:</b>\n<i>{html.escape(text[:800])}</i>")
            await bot.send_message(chat_id=PERSONAL_GROUP_ID, text=report, reply_markup=kb, parse_mode="HTML")
    except: pass

# --- ADMIN PANEL HANDLERLARI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in ADMIN_LIST:
        await message.answer("🤖 <b>Asosiy boshqaruv menyusi:</b>", reply_markup=main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    db_query("DELETE FROM user_state WHERE user_id=?", (callback.from_user.id,))
    await callback.message.edit_text("🤖 <b>Asosiy boshqaruv menyusi:</b>", reply_markup=main_menu(), parse_mode="HTML")

@dp.callback_query(F.data.in_({"menu_kw", "menu_gr"}))
async def show_sub_menus(callback: types.CallbackQuery):
    pref = "kw" if callback.data == "menu_kw" else "gr"
    title = "Kalit so'zlar" if pref == "kw" else "Guruhlar"
    await callback.message.edit_text(f"<b>{title} bo'limi:</b>", reply_markup=sub_menu(pref), parse_mode="HTML")

# --- O'CHIRISH LOGIKASI (TAYYOR VA XATOSIZ) ---
@dp.callback_query(F.data.startswith("del_list_"))
async def delete_list_menu(callback: types.CallbackQuery, force_pref=None):
    pref = force_pref if force_pref else callback.data.split("_")[2]
    
    if pref == "kw":
        data = db_query("SELECT id, keyword FROM keywords", fetch=True)
        text = "🗑 <b>O'chirmoqchi bo'lgan kalit so'zni tanlang:</b>"
    else:
        data = db_query("SELECT id, group_name FROM search_groups", fetch=True)
        text = "🗑 <b>O'chirmoqchi bo'lgan guruhni tanlang:</b>"

    kb = []
    if data:
        for item in data:
            kb.append([InlineKeyboardButton(text=f"❌ {item[1]}", callback_data=f"do_del_{pref}_{item[0]}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"menu_{pref}")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("do_del_"))
async def execute_delete(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    pref = parts[2] # 'kw' yoki 'gr'
    item_id = parts[3]

    if pref == "kw":
        db_query("DELETE FROM keywords WHERE id=?", (item_id,))
        await callback.answer("✅ Kalit so'z o'chirildi")
    else:
        res = db_query("SELECT group_id FROM search_groups WHERE id=?", (item_id,), fetch=True)
        if res:
            try: await client(functions.channels.LeaveChannelRequest(channel=res[0][0]))
            except: pass
        db_query("DELETE FROM search_groups WHERE id=?", (item_id,))
        await callback.answer("✅ Guruh o'chirildi")
    
    # Qayta o'sha list menyusiga qaytish
    await delete_list_menu(callback, force_pref=pref)

# --- QO'SHISH (KETMA-KET VA YAKUNLASH) ---
@dp.callback_query(F.data.startswith("add_"))
async def add_entry_start(callback: types.CallbackQuery):
    pref = callback.data.split("_")[1]
    db_query("REPLACE INTO user_state VALUES (?, ?, ?)", (callback.from_user.id, f"wait_{pref}", ""))
    
    txt = "📝 <b>Kalit so'zlarni yuboring:</b> (Vergul bilan yoki bittalab)" if pref == "kw" else \
          "📡 <b>Guruh havolasini yuboring:</b> (@guruh yoki link)"
    
    await callback.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Yakunlash", callback_data=f'menu_{pref}')]
    ]), parse_mode="HTML")

@dp.message(F.text)
async def handle_admin_inputs(message: types.Message):
    if message.from_user.id not in ADMIN_LIST: return
    state_res = db_query("SELECT state FROM user_state WHERE user_id=?", (message.from_user.id,), fetch=True)
    if not state_res: return
    state = state_res[0][0]

    if state == "wait_kw":
        words = [w.strip() for w in message.text.split(",") if w.strip()]
        for w in words: db_query("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (w,))
        await message.answer(f"✅ {len(words)} ta so'z qo'shildi. Yana yuboring yoki 'Yakunlash' tugmasini bosing.",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Yakunlash", callback_data='menu_kw')]]))

    elif state == "wait_gr":
        links = re.findall(r'(?:https?://)?t\.me/[a-zA-Z0-9_]{4,}|@[a-zA-Z0-9_]{4,}', message.text)
        if not links: return await message.answer("❌ Havola topilmadi. Qayta yuboring.")
        
        status = await message.answer("⏳ Ulanmoqda...")
        success = 0
        for link in links:
            try:
                clean = re.sub(r'/\d+$', '', link.strip().replace("https://t.me/", "").replace("@", ""))
                entity = await client.get_entity(clean)
                await client(functions.channels.JoinChannelRequest(channel=entity))
                eid = entity.id if str(entity.id).startswith("-100") else int(f"-100{entity.id}")
                db_query("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", (eid, entity.title))
                success += 1
                await asyncio.sleep(1)
            except: pass
            
        await status.edit_text(f"✅ {success} ta guruh qo'shildi.\nNavbatdagi havolani yuboring:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Yakunlash", callback_data='menu_gr')]]))

# --- KO'RISH VA STATUS ---
@dp.callback_query(F.data.startswith("view_"))
async def view_entries(callback: types.CallbackQuery):
    pref = callback.data.split("_")[1]
    table = "keywords" if pref == "kw" else "search_groups"
    col = "keyword" if pref == "kw" else "group_name"
    data = db_query(f"SELECT {col} FROM {table}", fetch=True)
    txt = f"📋 <b>Ro'yxat:</b>\n\n" + ("\n".join([f"• {k[0]}" for k in data]) if data else "Bo'sh")
    await callback.message.edit_text(txt[:4000], reply_markup=sub_menu(pref), parse_mode="HTML")

@dp.callback_query(F.data == "check_status")
async def check_status(callback: types.CallbackQuery):
    try:
        me = await client.get_me()
        k_count = db_query("SELECT COUNT(*) FROM keywords", fetch=True)[0][0]
        g_count = db_query("SELECT COUNT(*) FROM search_groups", fetch=True)[0][0]
        txt = f"⚙️ <b>Holat:</b>\n👤 Userbot: @{me.username}\n🔑 So'zlar: {k_count}\n📡 Guruhlar: {g_count}"
        await callback.message.edit_text(txt, reply_markup=main_menu(), parse_mode="HTML")
    except: await callback.answer("Userbot faol emas!")

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await client.start()
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    try: asyncio.run(main())
    except: pass
