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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- DB OPERATSIYALARI ---
def db_op(query, params=(), fetch=False):
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

# --- SUB MENYULAR ---
def sub_kb(mode):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data=f'add_{mode}')],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data=f'view_{mode}')],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f'del_{mode}')],
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
        db_op("DELETE FROM user_state WHERE user_id=?", (m.from_user.id,))
        await m.answer("🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "main_home")
async def go_home(c: types.CallbackQuery):
    db_op("DELETE FROM user_state WHERE user_id=?", (c.from_user.id,))
    await c.message.edit_text("🤖 <b>Boshqaruv paneli:</b>", reply_markup=main_kb(), parse_mode="HTML")
    await c.answer()

# --- BOLIMLAR (KEYWORDS VA GROUPS) ---
@dp.callback_query(F.data == "open_keywords")
async def open_kw(c: types.CallbackQuery):
    db_op("DELETE FROM user_state WHERE user_id=?", (c.from_user.id,))
    await c.message.edit_text("🔑 <b>Kalit so'zlar bo'limi:</b>", reply_markup=sub_kb('kw'), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "open_groups")
async def open_gr(c: types.CallbackQuery):
    db_op("DELETE FROM user_state WHERE user_id=?", (c.from_user.id,))
    await c.message.edit_text("📡 <b>Izlovchi guruhlar bo'limi:</b>", reply_markup=sub_kb('gr'), parse_mode="HTML")
    await c.answer()

# --- O'CHIRISH BO'LIMI (TO'LIQ QAYTA YOZILGAN) ---
@dp.callback_query(F.data == "del_kw")
async def del_keywords(c: types.CallbackQuery):
    data = db_op("SELECT id, keyword FROM keywords", fetch=True)
    
    if not data:
        await c.answer("❌ Kalit so'zlar ro'yxati bo'sh!", show_alert=True)
        return
    
    kb = []
    for item_id, keyword in data:
        kb.append([InlineKeyboardButton(text=f"❌ {keyword}", callback_data=f"remove_kw_{item_id}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data='open_keywords')])
    
    await c.message.edit_text(
        "🗑 <b>O'chiriladigan kalit so'zni tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )
    await c.answer()

@dp.callback_query(F.data == "del_gr")
async def del_groups(c: types.CallbackQuery):
    data = db_op("SELECT id, group_name FROM search_groups", fetch=True)
    
    if not data:
        await c.answer("❌ Guruhlar ro'yxati bo'sh!", show_alert=True)
        return
    
    kb = []
    for item_id, group_name in data:
        kb.append([InlineKeyboardButton(text=f"❌ {group_name}", callback_data=f"remove_gr_{item_id}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data='open_groups')])
    
    await c.message.edit_text(
        "🗑 <b>O'chiriladigan guruhni tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )
    await c.answer()

# --- O'CHIRISH AMALINI BAJARISH ---
@dp.callback_query(F.data.startswith("remove_kw_"))
async def remove_keyword(c: types.CallbackQuery):
    item_id = c.data.split("_")[2]
    
    db_op("DELETE FROM keywords WHERE id=?", (item_id,))
    await c.answer("✅ Kalit so'z o'chirildi!", show_alert=True)
    
    # Yangilangan ro'yxatni ko'rsatish
    data = db_op("SELECT id, keyword FROM keywords", fetch=True)
    
    if not data:
        await c.message.edit_text(
            "🔑 <b>Kalit so'zlar bo'limi:</b>\n\n✅ Barcha so'zlar o'chirildi!",
            reply_markup=sub_kb('kw'),
            parse_mode="HTML"
        )
        return
    
    kb = []
    for item_id, keyword in data:
        kb.append([InlineKeyboardButton(text=f"❌ {keyword}", callback_data=f"remove_kw_{item_id}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data='open_keywords')])
    
    await c.message.edit_text(
        "🗑 <b>O'chiriladigan kalit so'zni tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("remove_gr_"))
async def remove_group(c: types.CallbackQuery):
    item_id = c.data.split("_")[2]
    
    # Guruhdan chiqish
    res = db_op("SELECT group_id FROM search_groups WHERE id=?", (item_id,), fetch=True)
    if res:
        try:
            await client(functions.channels.LeaveChannelRequest(channel=res[0][0]))
        except:
            pass
    
    db_op("DELETE FROM search_groups WHERE id=?", (item_id,))
    await c.answer("✅ Guruh o'chirildi!", show_alert=True)
    
    # Yangilangan ro'yxatni ko'rsatish
    data = db_op("SELECT id, group_name FROM search_groups", fetch=True)
    
    if not data:
        await c.message.edit_text(
            "📡 <b>Izlovchi guruhlar bo'limi:</b>\n\n✅ Barcha guruhlar o'chirildi!",
            reply_markup=sub_kb('gr'),
            parse_mode="HTML"
        )
        return
    
    kb = []
    for item_id, group_name in data:
        kb.append([InlineKeyboardButton(text=f"❌ {group_name}", callback_data=f"remove_gr_{item_id}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data='open_groups')])
    
    await c.message.edit_text(
        "🗑 <b>O'chiriladigan guruhni tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )

# --- QO'SHISH BO'LIMI ---
@dp.callback_query(F.data == "add_kw")
async def add_keywords(c: types.CallbackQuery):
    db_op("REPLACE INTO user_state VALUES (?, ?, ?)", (c.from_user.id, "adding_kw", ""))
    
    await c.message.edit_text(
        "📝 <b>Kalit so'zlarni yuboring:</b>\n\n"
        "• Bir nechta so'z uchun vergul bilan ajrating\n"
        "• Masalan: <code>python, dasturlash, AI</code>\n\n"
        "✅ Istalgancha so'z qo'shishingiz mumkin",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Yakunlash", callback_data='open_keywords')]
        ]),
        parse_mode="HTML"
    )
    await c.answer()

@dp.callback_query(F.data == "add_gr")
async def add_groups(c: types.CallbackQuery):
    db_op("REPLACE INTO user_state VALUES (?, ?, ?)", (c.from_user.id, "adding_gr", ""))
    
    await c.message.edit_text(
        "📡 <b>Guruh linkini yuboring:</b>\n\n"
        "• Masalan: <code>@guruh_nomi</code>\n"
        "• Yoki: <code>https://t.me/guruh_nomi</code>\n\n"
        "✅ Istalgancha guruh qo'shishingiz mumkin\n"
        "📊 Har bir guruh alohida qo'shiladi",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Yakunlash", callback_data='open_groups')]
        ]),
        parse_mode="HTML"
    )
    await c.answer()

# --- TEXT HANDLER (GURUH QO'SHISH JARAYONI YAXSHILANGAN) ---
@dp.message(F.text)
async def text_handler(m: types.Message):
    if m.from_user.id not in ADMIN_LIST:
        return
    
    state = db_op("SELECT state FROM user_state WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not state:
        return
    
    st = state[0][0]
    
    # --- KALIT SO'Z QO'SHISH ---
    if st == "adding_kw":
        words = [w.strip() for w in m.text.split(",") if w.strip()]
        added = 0
        
        for w in words:
            try:
                db_op("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (w,))
                added += 1
            except:
                pass
        
        await m.answer(
            f"✅ <b>{added} ta kalit so'z qo'shildi!</b>\n\n"
            f"Yana yuboring yoki 'Yakunlash'ni bosing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Yakunlash", callback_data='open_keywords')]
            ]),
            parse_mode="HTML"
        )
    
    # --- GURUH QO'SHISH (HAR BIR GURUH ALOHIDA) ---
    elif st == "adding_gr":
        links = re.findall(r'(?:https?://)?t\.me/[a-zA-Z0-9_]{4,}|@[a-zA-Z0-9_]{4,}', m.text)
        
        if not links:
            await m.answer(
                "❌ <b>Havola noto'g'ri!</b>\n\n"
                "To'g'ri format:\n"
                "• @guruh_nomi\n"
                "• https://t.me/guruh_nomi",
                parse_mode="HTML"
            )
            return
        
        # Har bir guruh uchun alohida jarayon
        for idx, link in enumerate(links, 1):
            status_msg = await m.answer(
                f"⏳ <b>Guruh {idx}/{len(links)}</b>\n"
                f"📡 Ulanmoqda...",
                parse_mode="HTML"
            )
            
            try:
                # Link tozalash
                clean = re.sub(r'/\d+$', '', link.strip().replace("https://t.me/", "").replace("@", ""))
                
                # Guruh ma'lumotlarini olish
                ent = await client.get_entity(clean)
                
                # Guruhga qo'shilish
                await client(functions.channels.JoinChannelRequest(channel=ent))
                
                # Guruh ID ni to'g'ri formatlash
                gid = ent.id if str(ent.id).startswith("-100") else int(f"-100{ent.id}")
                
                # Bazaga saqlash
                db_op("INSERT OR IGNORE INTO search_groups (group_id, group_name) VALUES (?, ?)", 
                      (gid, ent.title))
                
                await status_msg.edit_text(
                    f"✅ <b>Muvaffaqiyatli qo'shildi!</b>\n\n"
                    f"📡 Guruh: <b>{ent.title}</b>\n"
                    f"🆔 ID: <code>{gid}</code>",
                    parse_mode="HTML"
                )
                
                await asyncio.sleep(2)
                
            except Exception as e:
                error_msg = str(e)
                
                if "FLOOD_WAIT" in error_msg:
                    wait_time = int(re.search(r'\d+', error_msg).group())
                    await status_msg.edit_text(
                        f"⚠️ <b>Kutish kerak: {wait_time} soniya</b>\n\n"
                        f"Telegram cheklovi. Keyinroq urinib ko'ring.",
                        parse_mode="HTML"
                    )
                elif "CHANNEL_PRIVATE" in error_msg:
                    await status_msg.edit_text(
                        f"❌ <b>Guruh yopiq yoki mavjud emas</b>\n\n"
                        f"Link: <code>{link}</code>",
                        parse_mode="HTML"
                    )
                elif "USERNAME_INVALID" in error_msg:
                    await status_msg.edit_text(
                        f"❌ <b>Guruh nomi noto'g'ri</b>\n\n"
                        f"Link: <code>{link}</code>",
                        parse_mode="HTML"
                    )
                else:
                    await status_msg.edit_text(
                        f"❌ <b>Xatolik yuz berdi</b>\n\n"
                        f"Sabab: {error_msg[:100]}",
                        parse_mode="HTML"
                    )
                
                await asyncio.sleep(1)
        
        # Yakuniy xabar
        await m.answer(
            f"🎉 <b>Jarayon yakunlandi!</b>\n\n"
            f"Yana guruh qo'shish uchun havola yuboring\n"
            f"yoki 'Yakunlash'ni bosing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Yakunlash", callback_data='open_groups')]
            ]),
            parse_mode="HTML"
        )

# --- KO'RISH ---
@dp.callback_query(F.data == "view_kw")
async def view_keywords(c: types.CallbackQuery):
    data = db_op("SELECT keyword FROM keywords", fetch=True)
    
    txt = "📋 <b>Kalit so'zlar ro'yxati:</b>\n\n"
    
    if data:
        txt += "\n".join([f"• {kw[0]}" for kw in data])
    else:
        txt += "❌ Ro'yxat bo'sh"
    
    await c.message.edit_text(txt[:4000], reply_markup=sub_kb('kw'), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "view_gr")
async def view_groups(c: types.CallbackQuery):
    data = db_op("SELECT group_name, group_id FROM search_groups", fetch=True)
    
    txt = "📋 <b>Izlovchi guruhlar:</b>\n\n"
    
    if data:
        for name, gid in data:
            txt += f"• {name}\n  <code>{gid}</code>\n\n"
    else:
        txt += "❌ Ro'yxat bo'sh"
    
    await c.message.edit_text(txt[:4000], reply_markup=sub_kb('gr'), parse_mode="HTML")
    await c.answer()

# --- STATUS ---
@dp.callback_query(F.data == "sys_status")
async def sys_status(c: types.CallbackQuery):
    try:
        me = await client.get_me()
        k = db_op("SELECT COUNT(*) FROM keywords", fetch=True)[0][0]
        g = db_op("SELECT COUNT(*) FROM search_groups", fetch=True)[0][0]
        
        txt = (f"⚙️ <b>Tizim holati:</b>\n\n"
               f"👤 Userbot: @{me.username}\n"
               f"🔑 Kalit so'zlar: {k} ta\n"
               f"📡 Guruhlar: {g} ta\n"
               f"✅ Holat: Faol")
        
        await c.message.edit_text(txt, reply_markup=main_kb(), parse_mode="HTML")
        await c.answer()
    except:
        await c.answer("❌ Userbot ishlamayapti!", show_alert=True)

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await client.start()
    print("✅ Bot va Userbot ishga tushdi!")
    await asyncio.gather(dp.start_polling(bot), client.run_until_disconnected())

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Bot to'xtatildi")
