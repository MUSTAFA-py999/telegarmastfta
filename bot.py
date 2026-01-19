import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, PollHandler, filters
from flask import Flask
from threading import Thread

# --- إعداد السيرفر الوهمي (لإبقاء البوت حياً على Render) ---
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
# -----------------------------------------------------------

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

polls_data = {}
vote_counts = {name: 0 for name in FIXED_OPTIONS}
current_summary_msg = None

async def send_polls_with_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_summary_msg, vote_counts, polls_data
    
    if not update.message or not update.message.text:
        return

    question = update.message.text
    chat_id = update.effective_chat.id
    
    vote_counts = {name: 0 for name in FIXED_OPTIONS}
    polls_data = {} 
    
    # --- التعديل الأول: جعل النص هو السؤال فقط ---
    # تم تغيير النص ليظهر السؤال بخط عريض، وتحته كلمة (النتائج)
    summary_text = f"**{question}**\n\n(جاري تجميع الأصوات...)"
    current_summary_msg = await context.bot.send_message(chat_id=chat_id, text=summary_text, parse_mode="Markdown")

    chunk_size = 10
    chunks = [FIXED_OPTIONS[i:i + chunk_size] for i in range(0, len(FIXED_OPTIONS), chunk_size)]

    for index, chunk in enumerate(chunks):
        # --- التعديل الثاني: إلغاء كلمة (قائمة 1) ---
        # نرسل question فقط بدون أي إضافات
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=question, 
            options=chunk,
            is_anonymous=True,
            allows_multiple_answers=False
        )
        polls_data[message.poll.id] = chunk
        await asyncio.sleep(1)

async def update_score_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global vote_counts
    poll = update.poll
    poll_id = poll.id
    
    if poll_id not in polls_data:
        return

    options_names = polls_data[poll_id]
    
    for i, option in enumerate(poll.options):
        name = options_names[i]
        vote_counts[name] = option.voter_count
    
    sorted_votes = sorted(vote_counts.items(), key=lambda item: item[1], reverse=True)
    active_votes = [item for item in sorted_votes if item[1] > 0]

    # --- التعديل الثالث: تحديث النص ليبقى السؤال فقط ---
    # نستخدم poll.question لنضمن بقاء السؤال كما هو في الأعلى
    text = f"**{poll.question}**\n\n"
    
    if not active_votes:
        text += "(لم يصوت أحد بعد)"
    else:
        rank = 1
        for name, count in active_votes:
            icon = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            text += f"{icon} **{name}**: {count}\n"
            rank += 1
            
    try:
        if current_summary_msg:
            await context.bot.edit_message_text(
                chat_id=current_summary_msg.chat_id,
                message_id=current_summary_msg.message_id,
                text=text,
                parse_mode="Markdown"
            )
    except Exception:
        pass

if __name__ == '__main__':
    keep_alive()
    
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        print("Error: TOKEN is not set!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), send_polls_with_summary)
        poll_handler = PollHandler(update_score_board)
        application.add_handler(msg_handler)
        application.add_handler(poll_handler)
        print("Bot is running...")
        application.run_polling()
