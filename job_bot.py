import asyncio
import aiohttp
import os
import json
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime
import time

# ==============================
# Настройки
# ==============================
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
SENT_FILE = "sent_jobs.json"
MAX_JOBS = 1000  # Ограничение, чтобы файл не рос бесконечно

# ==============================
# Инициализация
# ==============================
bot = Bot(token=TOKEN)
sent_jobs = set()

# ==============================
# Работа с файлом уже отправленных вакансий
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
    if len(sent_jobs) > MAX_JOBS:
        sent_jobs.pop()
    save_jobs()

# ==============================
# Фильтры вакансий
# ==============================
def is_relevant_job(title: str) -> bool:
    title = title.lower()
    if "qa" not in title:
        return False
    blacklist = ["lead", "manager", "head"]
    if any(word in title for word in blacklist):
        return False
    return True

def is_junior(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in ["junior", "trainee", "intern"])

# ==============================
# Отправка в телеграм
# ==============================
async def send_message(text):
    await bot.send_message(chat_id=CHAT_ID, text=text)

# ==============================
# Асинхронный запрос страницы
# ==============================
async def fetch(session, url, headers=None):
    async with session.get(url, headers=headers) as response:
        return await response.text()

# ==============================
# DOU.ua
# ==============================
async def check_dou(session):
    url = "https://jobs.dou.ua/vacancies/?search=qa"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", class_="vt")[:20]

    for job in jobs:
        title = job.text.strip()
        link = job["href"]

        if not is_relevant_job(title):
            continue
        if link in sent_jobs:
            continue

        add_job(link)
        prefix = "🟢 JUNIOR" if is_junior(title) else "QA"
        await send_message(f"{prefix} | DOU\n{title}\n{link}")

# ==============================
# Work.ua
# ==============================
async def check_workua(session):
    url = "https://www.work.ua/jobs-qa/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("div", class_="job-link")[:20]

    for job in jobs:
        link_tag = job.find("a")
        if not link_tag:
            continue
        title = link_tag.text.strip()
        link = "https://www.work.ua" + link_tag["href"]

        if not is_relevant_job(title):
            continue
        if link in sent_jobs:
            continue

        add_job(link)
        prefix = "🟢 JUNIOR" if is_junior(title) else "QA"
        await send_message(f"{prefix} | Work.ua\n{title}\n{link}")

# ==============================
# Rabota.ua
# ==============================
async def check_rabotaua(session):
    url = "https://robota.ua/zapros/qa/ukraine"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", href=True)[:50]

    for job in jobs:
        title = job.text.strip()
        link = job["href"]
        if not title or not is_relevant_job(title):
            continue

        if link.startswith("/"):
            link = "https://robota.ua" + link
        if link in sent_jobs:
            continue

        add_job(link)
        prefix = "🟢 JUNIOR" if is_junior(title) else "QA"
        await send_message(f"{prefix} | Rabota.ua\n{title}\n{link}")

# ==============================
# Основной цикл проверки вакансий
# ==============================
async def job_loop():
    load_jobs()
    async with aiohttp.ClientSession() as session:
        while True:
            print("LOOP STARTED 🔁", datetime.now())
            try:
                await check_dou(session)
                await check_workua(session)
                await check_rabotaua(session)
                print(f"{datetime.now()} ✅ done")
                await asyncio.sleep(300)  # 5 минут
            except Exception as e:
                print("❌ ERROR:", e)
                await asyncio.sleep(60)

# ==============================
# Запуск бота с вечным перезапуском
# ==============================
if __name__ == "__main__":
    while True:
        try:
            print("🚀 BOT START", datetime.now())
            asyncio.run(job_loop())
        except Exception as e:
            print("💥 CRASH:", e)
            time.sleep(5)
