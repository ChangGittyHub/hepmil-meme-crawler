import sqlite3
import requests
import os
from io import BytesIO
from datetime import datetime
import logging
import subprocess

from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether, PageBreak
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import matplotlib.pyplot as plt

from config import TELEGRAM_TOKEN, DB_PATH, CHART_FILE, MAX_MEMES_PER_DAY

# Logging Setup 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

def add_footer(canvas: canvas.Canvas, doc):
    page_num = canvas.getPageNumber()
    footer = f"Page {page_num} • Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(7.5 * inch, 0.5 * inch, footer)

def fetch_top_memes():
    logging.info("Fetching top memes from database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f'''
    SELECT title, author, score, url, shortlink, created_at
    FROM memes
    WHERE fetched_at >= datetime('now', '-1 day')
    ORDER BY score DESC
    LIMIT {MAX_MEMES_PER_DAY}
''')
    
    memes = cursor.fetchall()
    conn.close()
    logging.info(f"Retrieved {len(memes)} memes.")
    return memes

def generate_upvote_chart(memes):
    logging.info("Generating upvote distribution chart...")
    scores = [score for title, author, score, url, shortlink, created_at in memes]
    plt.figure(figsize=(6, 3))
    plt.bar(range(1, len(scores) + 1), scores)
    plt.title("Upvote Distribution")
    plt.xlabel("Top Meme Rank")
    plt.ylabel("Upvotes")
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

# PDF Story Builder
def build_story(memes, date_str):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MemeTitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        spaceBefore=6,
        spaceAfter=6
    ))

    story = []

    # Cover
    story.append(Spacer(1, 200))
    story.append(Paragraph("Meme Insights Report", styles["Title"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Curated from r/memes", styles["Heading2"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated on: {date_str}", styles["Normal"]))
    story.append(Spacer(1, 250))
    story.append(Paragraph("Prepared for HEPMIL Media", styles["Italic"]))
    story.append(PageBreak())

    # Body
    story.append(Paragraph("Top 20 Memes - Past 24 Hours", styles["Title"]))
    story.append(Spacer(1, 12))

    i = 1
    for meme in memes:
        title, author, score, url, shortlink, created_at = meme
        meme_block = []
        meme_block.append(Paragraph(f"{i}. {title}", styles["MemeTitle"]))
        meme_block.append(Paragraph(f"by u/{author} • {score} upvotes • Posted: {created_at}", styles["Italic"]))
        meme_block.append(Spacer(1, 6))

        try:
            response = requests.get(url, stream=True, timeout=5)
            content_type = response.headers.get("Content-Type", "")
            if response.status_code == 200 and "image" in content_type:
                img_data = BytesIO(response.content)
                img = Image(img_data, width=200, height=200)
                img.hAlign = 'CENTER'
                meme_block.append(img)
            else:
                meme_block.append(Paragraph(
                    f'<a href="{shortlink}">[View Meme on Reddit]</a>', styles["Italic"]
                ))
        except Exception as e:
            logging.exception(f"Failed to fetch image from {url}")
            meme_block.append(Paragraph(
                f'<a href="{shortlink}">[Failed to load media – View on Reddit]</a>', styles["Italic"]
            ))

        meme_block.append(Spacer(1, 14))
        story.append(KeepTogether(meme_block))
        i += 1

    # Chart
    chart_block = [
        Paragraph("Upvote Distribution", styles["Heading2"]),
        Spacer(1, 6),
        Image(CHART_FILE, width=400, height=200)
    ]
    story.append(Spacer(1, 20))
    story.append(KeepTogether(chart_block))

    return story

def generate_pdf_report():
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_file = f"top_memes_{date_str}.pdf"

        memes = fetch_top_memes()
        generate_upvote_chart(memes)
        story = build_story(memes, date_str)

        doc = SimpleDocTemplate(report_file, pagesize=letter)
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)

        logging.info(f"PDF report generated: {report_file}")
        return report_file
    except Exception as e:
        logging.exception("Failed to generate PDF report")
        raise

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heyyy there! Send /dailyreport to get today's top 20 memes in a PDF report.")

async def dailyreport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info("/dailyreport command received")
        await update.message.reply_text("Fetching the latest memes...")
        subprocess.run(["python", "reddit_scraper.py"], check=True)

        await update.message.reply_text("Generating your daily report...")
        filename = generate_pdf_report()
        await update.message.reply_text("Here is your daily report!")

        with open(filename, "rb") as f:
            await update.message.reply_document(document=InputFile(f, filename=filename))

        os.remove(filename)
        if os.path.exists(CHART_FILE):
            os.remove(CHART_FILE)
    except Exception as e:
        logging.exception("Error during /dailyreport")
        await update.message.reply_text("Something went wrong while generating your report.")

# Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dailyreport", dailyreport))

logging.info("Hepmemebot is now running.")
app.run_polling()
