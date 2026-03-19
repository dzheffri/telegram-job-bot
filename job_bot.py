import asyncio
import aiohttp
import os
import json
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from datetime import datetime

# ==============================
# Настройки
# ==============================
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

SENT_FILE = "sent_jobs.json"
APPLIED_FILE = "applied_jobs.json"

bot = Bot(token=TOKEN)
sent_jobs = set()
applied_jobs = set()

# ==============================
# Загрузка/сохранение данных
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
# Фильтры вакансий
# ==============================
def is_junior(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in ["junior", "trainee", "intern"])

def is_qa(title: str) -> bool:
    title = title.lower()
    return "qa" in title

# ==============================
# Генерация текста отклика
# ==============================
def generate_cover_letter(company: str) -> str:
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
# Отправка вакансии с кнопками
# ==============================
async def send_job(title: str, link: str, company: str):
    keyboard = [
        [
            InlineKeyboardButton("🚀 Откликнуться", callback_data=f"apply|{link}|{company}"),
            InlineKeyboardButton("✅ Уже откликнулся", callback_data=f"done|{link}")
        ]
    ]
    prefix = "🟢 JUNIOR" if is_junior(title) else "QA"
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"{prefix}\n{title}\n🏢 {company}\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# Обработка кнопок
# ==============================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("apply"):
        _, link, company = data.split("|")
        text = generate_cover_letter(company)
        await query.message.reply_text(f"📄 Текст:\n\n{text}\n🔗 {link}")

    elif data.startswith("done"):
        _, link = data.split("|")
        applied_jobs.add(link)
        save_applied()
        await query.edit_message_text("✅ Отмечено как откликнутую")

# ==============================
# Парсеры сайтов
# ==============================
async def check_dou(session):
    url = "https://jobs.dou.ua/vacancies/?search=qa"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers) as resp:
        html = await resp.text()
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", class_="vt")[:20]

    for job in jobs:
        title = job.text.strip()
        link = job["href"]
        company_tag = job.find_next("span", class_="company")
        company = company_tag.text.strip() if company_tag else "Компанія"

        if not is_qa(title):
            continue
        if link in sent_jobs or link in applied_jobs:
            continue
        add_job(link)
        await send_job(title, link, company)

async def check_workua(session):
    url = "https://www.work.ua/jobs-qa/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers) as resp:
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

async def check_rabotaua(session):
    url = "https://robota.ua/zapros/qa/ukraine"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers) as resp:
        html = await resp.text()
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", href=True)[:50]

    for job in jobs:
        title = job.text.strip()
        link = job["href"]
        if not title or not is_qa(title):
            continue
        if link.startswith("/"):
            link = "https://robota.ua" + link
        if link in sent_jobs or link in applied_jobs:
            continue
        add_job(link)
        await send_job(title, link, "Компанія")

# ==============================
# Фоновый цикл
# ==============================
async def job_loop():
    await asyncio.sleep(5)
    async with aiohttp.ClientSession() as session:
        while True:
            print("🔁 CHECK", datetime.now())
            load_data()
            try:
                await check_dou(session)
                await check_workua(session)
                await check_rabotaua(session)
            except Exception as e:
                print("❌ ERROR:", e)
            await asyncio.sleep(300)  # каждые 5 минут

# ==============================
# Главная функция
# ==============================
def main():
    load_data()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CallbackQueryHandler(button_handler))

    async def start_background(_app):
        asyncio.create_task(job_loop())

    app.post_init = start_background
    print("🚀 BOT START")
    app.run_polling()

if __name__ == "__main__":
    main()
