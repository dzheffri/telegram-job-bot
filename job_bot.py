
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime, timedelta

# Токен и chat_id берем из переменных окружения на сервере Railway
import os
TOKEN = os.getenv("TOKEN")  # добавьте в Railway Variables
CHAT_ID = int(os.getenv("CHAT_ID"))  # добавьте в Railway Variables

bot = Bot(token=TOKEN)
sent_jobs = set()  # чтобы не слать повторно

async def send_message(text):
    await bot.send_message(chat_id=CHAT_ID, text=text)

async def fetch(session, url, headers=None):
    async with session.get(url, headers=headers) as response:
        return await response.text()

# DOU.ua
async def check_dou(session):
    url = "https://jobs.dou.ua/vacancies/?search=qa"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", class_="vt")
    for job in jobs:
        title = job.text.strip()
        link = job["href"]
        if "junior" in title.lower() or "qa" in title.lower():
            if link not in sent_jobs:
                sent_jobs.add(link)
                await send_message(f"DOU.ua:\n{title}\n{link}")

# Work.ua
async def check_workua(session):
    url = "https://www.work.ua/jobs-qa-junior/"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("div", class_="job-link")
    for job in jobs:
        link_tag = job.find("a")
        if link_tag:
            title = link_tag.text.strip()
            link = "https://www.work.ua" + link_tag["href"]
            if "junior" in title.lower() or "qa" in title.lower():
                if link not in sent_jobs:
                    sent_jobs.add(link)
                    await send_message(f"Work.ua:\n{title}\n{link}")

# Rabota.ua
async def check_rabotaua(session):
    url = "https://rabota.ua/ru/zapros/qa"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", href=True)
    for job in jobs:
        title = job.text.strip()
        link = job["href"]
        if any(word in title.lower() for word in ["qa", "тест", "tester"]):
            if link.startswith("/"):
                link = "https://rabota.ua" + link
            if link not in sent_jobs:
                sent_jobs.add(link)
                await send_message(f"Rabota.ua:\n{title}\n{link}")

# Djinni через Playwright (headless браузер)


# Основной цикл проверки
async def job_check_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await check_dou(session)
                await check_workua(session)
                await check_rabotaua(session)
                await check_djinni()  # Djinni через браузер
                print(f"{datetime.now()}: Проверка вакансий завершена ✅")
                await asyncio.sleep(300)  # каждые 5 минут
            except Exception as e:
                print("Ошибка:", e)
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(job_check_loop())
