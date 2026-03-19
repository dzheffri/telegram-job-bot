import os
import json
import aiohttp
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, CommandHandler

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://yourapp.up.railway.app/webhook
PORT = int(os.getenv("PORT", 8443))

SENT_FILE = "sent_jobs.json"
APPLIED_FILE = "applied_jobs.json"

bot = Bot(token=TOKEN)
sent_jobs = set()
applied_jobs = set()

# ==============================
# Load / Save
# ==============================
def load_data():
    global sent_jobs, applied_jobs
    try:
        with open(SENT_FILE, "r") as f:
            sent_jobs = set(json.load(f))
    except:
        sent_jobs = set()
    try:
        with open(APPLIED_FILE, "r") as f:
            applied_jobs = set(json.load(f))
    except:
        applied_jobs = set()

def save_sent():
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_jobs), f)

def save_applied():
    with open(APPLIED_FILE, "w") as f:
        json.dump(list(applied_jobs), f)

def add_job(link):
    sent_jobs.add(link)
    save_sent()

# ==============================
# Filters
# ==============================
def is_junior(title):
    return any(x in title.lower() for x in ["junior", "trainee", "intern"])

def is_qa(title):
    return "qa" in title.lower()

# ==============================
# Cover Letter
# ==============================
def generate_cover_letter(company):
    return f"""Доброго дня!

Мене зацікавила ваша вакансія {company}.

Я початківець у QA, але вже маю практичний досвід:
самостійно розробив мобільний застосунок на Swift і повністю протестував його.

Працював із тест-кейсами, чек-листами, баг-репортами,
використовую Postman, Jira, TestRail, маю базові знання SQL та API.

Також створив Telegram-бота, який автоматично знаходить вакансії —
як приклад моєї ініціативності та технічних навичок 🙂

Буду радий можливості поспілкуватися!
"""

# ==============================
# Send Job Message
# ==============================
async def send_job(title, link, company):
    keyboard = [
        [
            InlineKeyboardButton("🚀 Откликнуться", callback_data=f"apply|{link}|{company}"),
            InlineKeyboardButton("✅ Уже откликнулся", callback_data=f"done|{link}")
        ]
    ]

    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"{'🟢 JUNIOR' if is_junior(title) else 'QA'}\n{title}\n🏢 {company}\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# Button Handler
# ==============================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("apply"):
        _, link, company = data.split("|")
        text = generate_cover_letter(company)
        await query.message.reply_text(f"📄 Текст для отклика:\n\n{text}\n\n🔗 {link}")
    elif data.startswith("done"):
        _, link = data.split("|")
        applied_jobs.add(link)
        save_applied()
        await query.edit_message_text("✅ Отмечено как откликнуто")

# ==============================
# Parsers
# ==============================
async def check_workua(session):
    url = "https://www.work.ua/jobs-qa/"
    async with session.get(url) as resp:
        html = await resp.text()
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("div", class_="job-link")[:20]

    for job in jobs:
        a = job.find("a")
        if not a:
            continue
        title = a.text.strip()
        link = "https://www.work.ua" + a["href"]
        company_tag = job.find("span", class_="company")
        company = company_tag.text.strip() if company_tag else "Компанія"

        if not is_qa(title):
            continue
        if link in sent_jobs or link in applied_jobs:
            continue

        add_job(link)
        await send_job(title, link, company)

# ==============================
# Background Loop
# ==============================
async def job_loop():
    await asyncio.sleep(5)
    while True:
        print("🔁 CHECK", datetime.now())
        load_data()
        try:
            async with aiohttp.ClientSession() as session:
                await check_workua(session)
        except Exception as e:
            print("❌ Ошибка:", e)
        await asyncio.sleep(300)  # 5 минут

# ==============================
# Webhook Setup
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен и работает!")

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Запуск фонового цикла
    async def start_background(_app):
        asyncio.create_task(job_loop())
    app.post_init = start_background

    # Устанавливаем webhook
    app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)

if __name__ == "__main__":
    main()
