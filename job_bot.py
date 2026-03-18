
    import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime

# Берем данные из Railway (Variables)
TOKEN = os.getenv("8618394268:AAHW0AT89GlV1jxz2LEgXWHFYwKXsOqjHM4")
CHAT_ID = int(os.getenv("566408696"))

bot = Bot(token=TOKEN)
sent_jobs = set()  # чтобы не дублировать вакансии


async def send_message(text):
    await bot.send_message(chat_id=CHAT_ID, text=text)


async def fetch(session, url, headers=None):
    async with session.get(url, headers=headers) as response:
        return await response.text()


# DOU
async def check_dou(session):
    url = "https://jobs.dou.ua/vacancies/?search=qa"
    headers = {"User-Agent": "Mozilla/5.0"}

    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")

    jobs = soup.find_all("a", class_="vt")

    for job in jobs:
        title = job.text.strip()
        link = job["href"]

        if ("junior" in title.lower() or "qa" in title.lower()) and link not in sent_jobs:
            sent_jobs.add(link)
            await send_message(f"DOU:\n{title}\n{link}")


# Djinni
async def check_djinni(session):
    url = "https://djinni.co/jobs/?primary_keyword=QA"
    headers = {"User-Agent": "Mozilla/5.0"}

    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")

    jobs = soup.find_all("a", class_="profile")

    for job in jobs:
        title = job.text.strip()
        link = "https://djinni.co" + job["href"]

        if "qa" in title.lower() and link not in sent_jobs:
            sent_jobs.add(link)
            await send_message(f"Djinni:\n{title}\n{link}")


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

            if ("junior" in title.lower() or "qa" in title.lower()) and link not in sent_jobs:
                sent_jobs.add(link)
                await send_message(f"Work.ua:\n{title}\n{link}")


# Rabota.ua
async def check_rabotaua(session):
    url = "https://rabota.ua/zapros/qa%20junior/вакансии"
    headers = {"User-Agent": "Mozilla/5.0"}

    html = await fetch(session, url, headers)
    soup = BeautifulSoup(html, "html.parser")

    jobs = soup.find_all("div", class_="f-vacancy-title")

    for job in jobs:
        link_tag = job.find("a")
        if link_tag:
            title = link_tag.text.strip()
            link = "https://rabota.ua" + link_tag["href"]

            if link not in sent_jobs:
                sent_jobs.add(link)
                await send_message(f"Rabota.ua:\n{title}\n{link}")


async def job_check_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await check_dou(session)
                await check_djinni(session)
                await check_workua(session)
                await check_rabotaua(session)

                print(f"{datetime.now()}: Проверка вакансий завершена ✅")

                await asyncio.sleep(300)  # каждые 5 минут

            except Exception as e:
                print("Ошибка:", e)
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(job_check_loop())
