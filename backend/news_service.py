import feedparser
from urllib.parse import quote_plus #convert space into + sign
from datetime import datetime, timezone, timedelta
import re
import html
import time
import urllib.request

search_queries=['"job scam" Malaysia', '"fake job" Malaysia', '"recruitment scam" Malaysia',
    '"part-time job scam" Malaysia', '"work from home scam" Malaysia']

google_news_rss="https://news.google.com/rss/search?q={query}&hl=en-MY&gl=MY&ceid=MY:en"

news_source={
    "the star", "the sun malaysia", "free malaysia today", "malay mail", "the vibes", 
    "new straits times", "bernama", "malaysiakini", "the edge malaysia", "astro awani", 
    "sinar daily", "harian metro", "berita harian", "china press", "sin chew daily", "the malaysian reserve",
}

stopwords={
    "job", "jobs", "scam", "scams", "fake", "offer", "offers",
    "online", "malaysia", "after", "with", "from", "that",
    "over", "into", "amid", "about", "this", "have",
}

def clean_summary(summary):
    """Remove HTML tags and clean the article summary."""
    summary=html.unescape(summary or "")
    summary=re.sub(r"<[^>]+>"," ",summary)
    summary=re.sub(r"\s+"," ",summary)
    return summary.strip()

def is_job_scam_related(title,summary):
    """Keep articles related to both jobs and scams."""
    content=(title+" "+summary).lower()

    job_keywords=[
        "job", "recruitment", "recruiter", "hiring",
        "employment", "vacancy", "work from home",
        "part-time", "part time", "jobseeker",
        "job seeker", "career"
    ]

    scam_keywords=[
        "scam", "fraud", "fake", "impersonat",
        "warning", "alert", "cheated", "fraudulent"
    ]

    has_job_keyword=any(word in content for word in job_keywords)
    has_scam_keyword=any(word in content for word in scam_keywords)

    return has_job_keyword and has_scam_keyword

def clean_title(title):
    """Remove the publisher name at the end of the title."""
    return re.sub(r"\s+-\s+[^-]+$","",title).strip()

def is_malaysia(title, source):
    """Only accept articles from approved Malaysian news publishers."""
    #title_lower=title.lower()
    source_lower=source.lower()
    return any(outlet in source_lower for outlet in news_source)

def significant_words(title):
    """Extract meaningful words from an article title."""
    return {
        word
        for word in re.findall(r"[a-z0-9]+", title.lower())
        if len(word)>3 and word not in stopwords
    }

def is_duplicate_story(title, kept_titles, min_shared=3):
    """Check whether a title is too similar to an existing article."""
    words=significant_words(title)

    return any(
        len(words & significant_words(existing_title)) >= min_shared
        for existing_title in kept_titles
    )

def is_unrelated_company_hack(title, summary):
    """Exclude company hacking stories involving fake job interviews."""
    content=(title+" "+summary).lower()

    hacking_keywords=[
        "hacker", "hackers", "hacked", "heist", "infiltrated", "compromised"
    ]

    interview_keywords=[
        "fake job interview", "fake job interviews", "job interview", "job interviews"
    ]

    has_hacking_keyword=any(word in content for word in hacking_keywords)
    has_interview_keyword=any(word in content for word in interview_keywords)

    return has_hacking_keyword and has_interview_keyword

def fetch_job_scam_news(max_articles=10, days=60):
    candidates=[]

    cutoff_date=datetime.now(timezone.utc)-timedelta(days=days)

    for query_index, search_query in enumerate(search_queries):
        if query_index>0:
            time.sleep(2)
        encoded_query=quote_plus(search_query)
        feed_url=google_news_rss.format(query=encoded_query)
        feed=None

        for attempt in range(3):
            try:
                request=urllib.request.Request(
                    feed_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 JobShield News Reader",
                        "Accept": "application/rss+xml, application/xml"
                    }
                )
                with urllib.request.urlopen(request,timeout=15) as response:
                    feed_data=response.read()

                feed=feedparser.parse(feed_data)
                if feed.bozo and not feed.entries:
                    raise ValueError("Invalid or unreadable RSS feed")
                break
            except Exception as error:
                if attempt<2:
                    print(
                        f"Attempt {attempt + 1} failed for "
                        f"{search_query}: {error}"
                    )
                    time.sleep(2*(attempt + 1))
                else:
                    print(
                        f"Could not retrieve feed after 3 attempts: "
                        f"{search_query}: {error}"
                    )
        if feed is None:
            continue
        for entry in feed.entries:
            ori_title=entry.get("title","").strip()
            url=entry.get("link","").strip()
            summary=clean_summary(entry.get("summary",""))
            source=entry.get("source",{}).get("title", "Unknown source").strip()

            if not ori_title or not url:
                continue
            title=clean_title(ori_title)
            
            published=entry.get("published_parsed")
            if not published:
                continue

            published_date=datetime(
                *published[:6],
                tzinfo=timezone.utc
            )

            if published_date<cutoff_date:
                continue
            if not is_job_scam_related(title, summary):
                continue
            if not is_malaysia(title, source):
                continue
            if is_unrelated_company_hack(title, summary):
                continue
                
            candidates.append({
                "title":title,
                "source":source,
                "published_at":published_date.isoformat(),
                "summary":summary,
                "url":url
            })

    candidates.sort(
        key=lambda article:article["published_at"],
        reverse=True
    )

    articles=[]
    seen_urls=set()
    seen_titles=set()
    for article in candidates:
        title_key=article["title"].lower()
        url=article["url"]
        if url in seen_urls or title_key in seen_titles:
            continue

        kept_titles = [a["title"] for a in articles]

        if is_duplicate_story(article["title"], kept_titles):
            continue

        articles.append(article)
        seen_urls.add(url)
        seen_titles.add(title_key)
    return articles[:max_articles]
if __name__=="__main__":
    print("\nSearching for Malaysian job scam news...\n")
    news_articles=fetch_job_scam_news(max_articles=10)
    for index, article in enumerate(news_articles, start=1):
        print("="*60)
        print(f"Article {index}")
        print("Title:", article["title"])
        print("Source:", article["source"])
        print("Date:", article["published_at"])
        print("Summary:", article["summary"][:300])
        print("URL:", article["url"])
        print()
    