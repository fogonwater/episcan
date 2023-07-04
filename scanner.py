from datetime import date, timedelta, datetime
import json
from hashlib import sha256
import operator
import re
import sqlite3
import credentials
from newsapi import NewsApiClient

NEWSAPI = NewsApiClient(api_key=credentials.NEWSAPI_KEY)
# KEYWORD_QUERIES = ["rabies", "measles", "dengue", "meningitis"]
KEYWORD_QUERIES = ["dengue", "measles", "zika"]


def striphtml(data):
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
    text = re.sub(r"\s+", " ", text)
    return striphtml(text)


def striphtml(data):
    p = re.compile(r"<.*?>")
    return p.sub("", data)


class Harvester:
    def __init__(self, lookback_period=3, db_name="epinews.db"):
        self.start_date = date.today() - timedelta(days=lookback_period)
        try:
            # Wrap db connection in try/finally to ensure we close connection
            self.conn = sqlite3.connect(db_name)
            self.conn.row_factory = sqlite3.Row
            self.setup_db()
            c = self.conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM articles")
            num_articles_start = c.fetchone()[0]
            # Harvest new articles
            self.harvest()
            # Get our article table count after harvesting and print counts
            c.execute(f"SELECT COUNT(*) FROM articles")
            num_articles_end = c.fetchone()[0]
            print(f"There are {num_articles_end} rows in the articles table.")
            print(
                f"This includes {num_articles_end - num_articles_start} new article(s)"
            )
            self.export()
        except Exception as e:
            # Handle the exception
            print("* An error occurred:", str(e))
        finally:
            # Close the database connection
            self.conn.close()
            print(f"Closed connection to: {db_name}")

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
        source_id = article["source"]["id"]
        source_name = article["source"]["name"]
        author = article["author"]
        url = article["url"]
        urlToImage = article["urlToImage"]
        publishedAt = datetime.strptime(article["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        content = article["content"]
        retrievedAt = datetime.now()

        # Generate unique internal_id based on publish date, source, title
        internal_id = sha256(f"{publishedAt}{source_name}{title}".encode()).hexdigest()

        if query in "*".join([title.lower(), description.lower(), content.lower()]):
            # Check if article with the same internal_id already exists
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
                # print(f"Added: {title}")
                self.conn.commit()

    def export(self, dst_file="data/articles.json"):
        c = self.conn.cursor()

        c.execute("SELECT * FROM articles")
        rows = c.fetchall()

        result = []
        columns = [description[0] for description in c.description]

        for row in rows:
            item = dict(zip(columns, row))
            item["query"] = item["query"].split("|")
            result.append(item)

        result.sort(key=operator.itemgetter("publishedAt"), reverse=True)

        with open(dst_file, "w") as json_file:
            publish_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            json.dump(
                {
                    "last_updated": publish_time,
                    "article_count": len(result),
                    "articles": result[:200],
                },
                json_file,
                indent=2,
            )


# Intit
harvester = Harvester()
