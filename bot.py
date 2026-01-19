import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, PollHandler, filters
from flask import Flask
from threading import Thread

# --- إعداد السيرفر الوهمي ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------

# القائمة الثابتة
FIXED_OPTIONS = [
    "مصطفى شامل", "محمد حارث", "هند", "زمزم", "طيبة", 
    "محمود", "يوسف", "محمد اثير", "كفاح", "عبد القادر", 
    "عبد الرحمن احمد", "مصطفى عمر", "أية", "رياض", "عبد الوهاب", 
    "ذالفاء", "مصطفى محمد حازم", "مريم", "سدرة", "مصطفى محمد عبد المنعم", 
    "عبدالله", "خديجة", "فنر", "يونس", "سراج", 
    "محمد ماجد", "عبد الرحمن زياد", "ديمة"
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

chats_data = {} 
poll_ownership = {}

async def send_polls_with_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    question = update.message.text
    chat_id = update.effective_chat.id
    
    chats_data[chat_id] = {
        'votes': {name: 0 for name in FIXED_OPTIONS},
        'poll_map': {},
        'msg': None,
        'original_question': question
    }
    
    # --- التعديل الجمالي 1: إضافة خط فاصل سميك ---
    summary_text = f"📊 **{question}**\n━━━━━━━━━━━━━━━━━\n(جاري تجميع الأصوات...)"
    
    sent_msg = await context.bot.send_message(chat_id=chat_id, text=summary_text, parse_mode="Markdown")
    chats_data[chat_id]['msg'] = sent_msg

    chunk_size = 10
    chunks = [FIXED_OPTIONS[i:i + chunk_size] for i in range(0, len(FIXED_OPTIONS), chunk_size)]

    for index, chunk in enumerate(chunks):
        # القائمة الأولى تأخذ السؤال، والباقي سهم
        if index == 0:
            poll_text = question
        else:
            poll_text = "⬇️"

        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=poll_text, 
            options=chunk,
            is_anonymous=True,
            allows_multiple_answers=False
        )
        
        poll_id = message.poll.id
        poll_ownership[poll_id] = chat_id
        chats_data[chat_id]['poll_map'][poll_id] = chunk
        
        await asyncio.sleep(1)

async def update_score_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.poll
    poll_id = poll.id
    
    chat_id = poll_ownership.get(poll_id)
    if not chat_id or chat_id not in chats_data:
        return

    chat_info = chats_data[chat_id]
    
    if poll_id not in chat_info['poll_map']:
        return
        
    options_names = chat_info['poll_map'][poll_id]
    
    for i, option in enumerate(poll.options):
        name = options_names[i]
        chat_info['votes'][name] = option.voter_count
    
    sorted_votes = sorted(chat_info['votes'].items(), key=lambda item: item[1], reverse=True)
    active_votes = [item for item in sorted_votes if item[1] > 0]

    original_q = chat_info['original_question']
    
    # --- التعديل الجمالي 2: تنسيق النتائج مع الخط الفاصل ---
    text = f"📊 **{original_q}**\n━━━━━━━━━━━━━━━━━\n"
    
    if not active_votes:
        text += "(لم يصوت أحد بعد)"
    else:
        rank = 1
        for name, count in active_votes:
            # تمييز المراكز الثلاثة الأولى
            if rank == 1:
                icon = "🥇"
            elif rank == 2:
                icon = "🥈"
            elif rank == 3:
                icon = "🥉"
            else:
                icon = f"▫️ {rank}." # شكل أجمل للمراتب الباقية
            
            text += f"{icon} {name} ⟵ ({count})\n"
            rank += 1
            
    try:
        scoreboard_msg = chat_info['msg']
        if scoreboard_msg:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=scoreboard_msg.message_id,
                text=text,
                parse_mode="Markdown"
            )
    except Exception:
        pass

if __name__ == '__main__':
    keep_alive()
    
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        print("Error: TOKEN is missing!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND) & (~filters.UpdateType.EDITED_MESSAGE), send_polls_with_summary)
        poll_handler = PollHandler(update_score_board)
        
        application.add_handler(msg_handler)
        application.add_handler(poll_handler)
        
        print("Bot is running...")
        application.run_polling()
