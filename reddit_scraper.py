import praw
import sqlite3
from datetime import datetime
import logging

from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
    DB_PATH, MAX_MEMES_PER_DAY
)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Reddit Client Setup
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Connect to DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if Table Exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT UNIQUE,
    title TEXT,
    author TEXT,
    score INTEGER,
    url TEXT,
    shortlink TEXT,
    created_at TEXT,  
    fetched_at TEXT 
    )
''')

# Fetch Top Posts
logging.info("Scraping top posts from r/memes...")
subreddit = reddit.subreddit("memes")
top_posts = subreddit.top(time_filter='day', limit=MAX_MEMES_PER_DAY)

added, updated = 0, 0

for post in top_posts:
    try:
        post_id = post.id
        title = post.title
        author = str(post.author) if post.author else "[deleted]"
        score = post.score
        url = post.url
        shortlink = post.shortlink
        created_at = datetime.fromtimestamp(post.created_utc).isoformat()
        fetched_at = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO memes (post_id, title, author, score, url, shortlink, created_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                title = excluded.title,
                author = excluded.author,
                score = excluded.score,
                url = excluded.url,
                shortlink = excluded.shortlink,
                created_at = excluded.created_at
        ''', (post_id, title, author, score, url, shortlink, created_at, fetched_at))

        if cursor.rowcount == 1:
            added += 1
        else:
            updated += 1

        logging.info(f" Saved: {title} by u/{author} | Score: {score}")
    except Exception as e:
        logging.exception(f"Error processing post ID: {post.id}")

conn.commit()
conn.close()

logging.info(f"Scraping complete — {added} new posts, {updated} updated.")
