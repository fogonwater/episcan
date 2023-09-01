from datetime import date, timedelta, datetime
import json
from hashlib import sha256
import os
import re
import sqlite3
from newsapi import NewsApiClient
from settings import KEYWORD_QUERIES, SOURCE_IGNORE

NEWSAPI = NewsApiClient(api_key=os.environ.get("NEWSAPI_KEY"))


def strip_html(data):
    p = re.compile(r"<.*?>")
    return p.sub("", data)


def str_squish(text):
    """
    Strip whitespace + multiple whitespaces with a single space
    and HTML tags
    """
    if not text:
        return ""
    text = text.strip()
    text = strip_html(text)
    text = re.sub(r"\s+", " ", text)
    return text


class Harvester:
    def __init__(self, lookback_period=4, db_name="epinews.db"):
        self.start_date = date.today() - timedelta(days=lookback_period)
        self.num_articles_start = 0
        self.count_articles_new = 0
        self.conn = None
        # Wrap db connection in try/finally to ensure we close connection
        try:
            self.connect_to_db(db_name)
            self.setup_db()
            # Establish article count prior to harvest
            c = self.conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM articles")
            self.num_articles_start = c.fetchone()[0]
            # Harvest new articles, update counts and export JSON
            self.harvest()
            self.update_article_counts()
            self.export()
        except Exception as e:
            # Handle the exception
            print("* An error occurred:", str(e))
        finally:
            # Close the database connection
            self.close_db_connection(db_name)

    def connect_to_db(self, db_name):
        """Establish a connection to the database"""
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row

    def setup_db(self):
        """Setup articles table if it doesn't already exist"""
        c = self.conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                source_id TEXT,
                source_name TEXT,
                author TEXT,
                title TEXT,
                description TEXT,
                url TEXT,
                urlToImage TEXT,
                publishedAt TEXT,
                content TEXT,
                retrievedAt TEXT,
                internal_id TEXT
            )
        """
        )

    def close_db_connection(self, db_name):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
        print(f"Closed connection to: {db_name}")

    def harvest(self):
        """Loop through queries and harvest new articles"""
        for query in KEYWORD_QUERIES:
            articles = self.fetch_articles(query)
            for article in articles:
                self.process_article(query, article)

    def fetch_articles(self, query):
        """Fetch the articles matching query from the News API"""
        r = NEWSAPI.get_everything(
            q=query,
            from_param=self.start_date.strftime("%Y-%m-%d"),
            sort_by="relevancy",
        )
        if "articles" in r:
            print(f"Got {len(r['articles'])} {query} articles")
            return r["articles"]
        return []

    def process_article(self, query, article):
        """
        Extract data fields for each article, then insert into the
        database if it doesn’t already exist
        """
        c = self.conn.cursor()
        publishedAt = article["publishedAt"]
        title = str_squish(article["title"])
        description = str_squish(article["description"])
        if not publishedAt or not title:
            return
        source_id = article["source"]["id"]
        source_name = article["source"]["name"]
        author = article["author"]
        url = article["url"]
        urlToImage = article["urlToImage"]
        publishedAt = datetime.strptime(article["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        content = str_squish(article["content"])
        retrievedAt = datetime.now()

        # Check if the query is in the title, description, or content of the article
        if query not in "*".join([title.lower(), description.lower(), content.lower()]):
            return
        # Check if source is in ignore list
        if source_name in SOURCE_IGNORE:
            return

        # Generate unique internal_id based on publish date, source, title
        internal_id = sha256(f"{publishedAt}{source_name}{title}".encode()).hexdigest()

        # Check if an article with the same internal_id already exists
        c.execute("SELECT * FROM articles WHERE internal_id = ?", (internal_id,))
        existing = c.fetchone()
        if existing and query not in existing["query"]:
            # Update the query field of the record with a new value
            new_query = "|".join([existing["query"], query])

            c.execute(
                "UPDATE articles SET query = ? WHERE internal_id = ?",
                (
                    new_query,
                    internal_id,
                ),
            )
            self.conn.commit()

        elif existing is None:
            # Insert the new article into articles table
            c.execute(
                """
                INSERT INTO articles (query, source_id, source_name, author, title, description, url, urlToImage, publishedAt, content, retrievedAt, internal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    query,
                    source_id,
                    source_name,
                    author,
                    title,
                    description,
                    url,
                    urlToImage,
                    publishedAt,
                    content,
                    retrievedAt,
                    internal_id,
                ),
            )
            self.conn.commit()

    def update_article_counts(self):
        """Print the count of new articles harvested"""
        c = self.conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM articles")
        num_articles_end = c.fetchone()[0]
        print(f"There are {num_articles_end} rows in the articles table.")
        self.count_articles_new = num_articles_end - self.num_articles_start
        print(f"This includes {self.count_articles_new} new article(s)")

    def export(self, dst_file="data/articles.json"):
        c = self.conn.cursor()

        c.execute("SELECT * FROM articles ORDER BY publishedAt DESC LIMIT 300")
        rows = c.fetchall()

        result = []
        columns = [description[0] for description in c.description]

        for row in rows:
            item = dict(zip(columns, row))
            if item["source_name"] in SOURCE_IGNORE:
                continue
            item["query"] = item["query"].split("|")
            pub_at = datetime.strptime(item["publishedAt"], "%Y-%m-%d %H:%M:%S")
            item["description"] = str_squish(item["description"])
            item["publishedAtLabel"] = str_squish(pub_at.strftime("%b %e"))
            result.append(item)

        with open(dst_file, "w") as json_file:
            publish_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            json.dump(
                {
                    "last_updated": publish_time,
                    "count_articles_total": len(result),
                    "count_articles_new": self.count_articles_new,
                    "articles": result[:200],
                },
                json_file,
                indent=2,
            )


# Intitialise the harvester
harvester = Harvester()
