import asyncio
import aiohttp
import os
import json
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler
from datetime import datetime
import time

# ==============================
# НАСТРОЙКИ
# ==============================
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

SENT_FILE = "sent_jobs.json"
APPLIED_FILE = "applied_jobs.json"

bot = Bot(token=TOKEN)

sent_jobs = set()
applied_jobs = set()

# ==============================
# LOAD / SAVE
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

def save_applied():
    with open(APPLIED_FILE, "w") as f:
        json.dump(list(applied_jobs), f)

def add_job(link):
    sent_jobs.add(link)
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_jobs), f)

# ==============================
# ФИЛЬТРЫ
# ==============================
def is_junior(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in ["junior", "trainee", "intern"])

def is_qa(title: str) -> bool:
    return "qa" in title.lower()

# ==============================
# COVER LETTER
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
# TELEGRAM
# ==============================
async def send_job(title, link, source, company):
    keyboard = [
        [
            InlineKeyboardButton("🚀 Откликнуться", callback_data=f"apply|{link}|{company}"),
            InlineKeyboardButton("✅ Уже откликнулся", callback_data=f"done|{link}")
        ]
    ]

    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"🟢 JUNIOR | {source}\n{title}\n🏢 {company}\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# CALLBACK HANDLER
# ==============================
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("apply"):
        _, link, company = data.split("|")

        text = generate_cover_letter(company)

        await query.message.reply_text(f"📄 Текст для отклика:\n\n{text}")
        await query.message.reply_text(f"🔗 Открыть вакансию:\n{link}")

    elif data.startswith("done"):
        _, link = data.split("|")
        applied_jobs.add(link)
        save_applied()
        await query.edit_message_text("✅ Отмечено как откликнуто")

# ==============================
# FETCH
# ==============================
async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

# ==============================
# WORK.UA
# ==============================
async def check_workua(session):
    url = "https://www.work.ua/jobs-qa/"
    html = await fetch(session, url)

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

        if not is_qa(title) or not is_junior(title):
            continue

        if link in sent_jobs or link in applied_jobs:
            continue

        add_job(link)
        await send_job(title, link, "Work.ua", company)

# ==============================
# LOOP
# ==============================
async def job_loop():
    load_data()

    async with aiohttp.ClientSession() as session:
        while True:
            print("🔁 LOOP", datetime.now())

            try:
                await check_workua(session)
                await asyncio.sleep(300)
            except Exception as e:
                print("ERROR:", e)
                await asyncio.sleep(60)

# ==============================
# START
# ==============================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CallbackQueryHandler(button_handler))

    # запуск фоновой задачи правильно
    async def on_startup(app):
        app.create_task(job_loop())

    app.post_init = on_startup

    app.run_polling()

if __name__ == "__main__":
    main()
