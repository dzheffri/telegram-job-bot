import asyncio
import aiohttp
import os
import json
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler
from datetime import datetime

# ==============================
# Настройки
# ==============================
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

SENT_FILE = "sent_jobs.json"

bot = Bot(token=TOKEN)
sent_jobs = set()


# ==============================
# Загрузка/Сохранение вакансий
# ==============================
def load_jobs():
    global sent_jobs
    try:
        with open(SENT_FILE, "r") as f:
            sent_jobs = set(json.load(f))
    except:
        sent_jobs = set()


def save_jobs():
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_jobs), f)


def add_job(link):
    sent_jobs.add(link)
    save_jobs()


# ==============================
# Фильтры
# ==============================
def is_junior(title: str) -> bool:
    return any(word in title.lower() for word in ["junior", "trainee", "intern"])


def is_qa(title: str) -> bool:
    return "qa" in title.lower()


# ==============================
# Отправка вакансии в Telegram
# ==============================
async def send_job(title, link, company):
    prefix = "🟢 JUNIOR" if is_junior(title) else "QA"
    keyboard = [
        [InlineKeyboardButton("✅ Уже откликнулся", callback_data=f"done|{link}")]
    ]
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"{prefix} | {company}\n{title}\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==============================
# Callback для кнопок
# ==============================
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("done"):
        _, link = data.split("|")
        add_job(link)
        await query.edit_message_text("✅ Отмечено как отправленное")


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
        company = "DOU.ua"

        if not is_qa(title):
            continue
        if link in sent_jobs:
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
        company = company_tag.text.strip() if company_tag else "Work.ua"

        if not is_qa(title):
            continue
        if link in sent_jobs:
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
        if link in sent_jobs:
            continue
        add_job(link)
        await send_job(title, link, "Rabota.ua")


# ==============================
# Фоновый цикл проверки вакансий
# ==============================
async def job_loop():
    await asyncio.sleep(5)
    async with aiohttp.ClientSession() as session:
        while True:
            print("🔁 CHECK", datetime.now())
            try:
                await check_dou(session)
                await check_workua(session)
                await check_rabotaua(session)
            except Exception as e:
                print("❌ ERROR:", e)
            await asyncio.sleep(300)  # 5 минут


# ==============================
# MAIN
# ==============================
def main():
    load_jobs()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CallbackQueryHandler(button_handler))

    async def start_background(_app):
        asyncio.create_task(job_loop())

    app.post_init = start_background

    print("🚀 BOT START")
    app.run_polling()


if __name__ == "__main__":
    main()
