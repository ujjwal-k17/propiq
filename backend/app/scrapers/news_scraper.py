"""
News Scraper
============
Fetches news about real estate developers and projects, then classifies
each article for sentiment and due-diligence category.

Sources (in order of preference):
  1. NewsAPI (NEWSAPI_KEY in .env)
  2. Google News RSS (no key required, but rate-limited)

Sentiment analysis (MVP keyword-based, no external AI call):
  - 2+ negative keywords  → critical / score −0.8
  - 1 negative keyword    → negative / score −0.4
  - 1+ positive keywords  → positive / score +0.6
  - Otherwise             → neutral  / score +0.1

In development mode realistic mock articles are returned so the pipeline
runs without a NewsAPI subscription.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.developer import Developer
from app.models.news_item import NewsCategory, NewsItem, SentimentLabel
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


NEGATIVE_KEYWORDS: list[str] = [
    "delay", "delayed", "stall", "stalled", "stuck", "halt", "halted",
    "NCLT", "insolvency", "fraud", "fraudulent", "complaint", "complaints",
    "refund", "cancel", "cancelled", "bankrupt", "bankruptcy", "default",
    "defaulted", "foreclosure", "seized", "attachment", "possession denied",
    "homebuyer agony", "builder betrayal", "duped", "cheated",
]

POSITIVE_KEYWORDS: list[str] = [
    "delivered", "completed", "handover", "OC received", "award",
    "on schedule", "ahead of schedule", "record sales", "strong demand",
    "expansion", "IPO", "new launch", "partnered",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "nclt": ["NCLT", "insolvency", "IRP", "liquidation", "moratorium", "CIRP"],
    "financial_stress": ["bankrupt", "default", "NPA", "debt", "stressed", "fraud", "seized"],
    "delay": ["delay", "stall", "stuck", "halt", "possession denied", "overdue", "late"],
    "fraud": ["fraud", "cheated", "duped", "mislead", "misrepresent", "scam", "FIR"],
    "positive": POSITIVE_KEYWORDS,
}

SEARCH_TEMPLATES: list[str] = [
    "{entity} real estate news India",
    "{entity} RERA complaint",
    "{entity} project delay",
    "{entity} NCLT insolvency",
    "{entity} possession homebuyer",
]


# ── Mock news data ────────────────────────────────────────────────────────────

_MOCK_NEWS: dict[str, list[dict]] = {
    "default": [
        {
            "headline": "{entity}: Strong Sales in Q1 FY2025, Revenue Grows 28%",
            "summary": "{entity} reported strong sales momentum driven by demand from end-users and NRI buyers. The developer's residential portfolio saw 28% year-on-year revenue growth.",
            "url": "https://economictimes.indiatimes.com/example-1",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(),
            "source": "Economic Times",
        },
        {
            "headline": "Real estate demand remains robust in metro cities: {entity}",
            "summary": "Industry leaders including {entity} confirm sustained demand across Mumbai and Bengaluru micro-markets. Affordability and infrastructure improvements cited as key drivers.",
            "url": "https://housing.com/news/example-2",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "source": "Housing.com",
        },
    ],
    "Lodha Developers Pvt Ltd": [
        {
            "headline": "Lodha World One receives OC; Handover begins for 200 families",
            "summary": "Lodha World One, the supertall residential tower in Lower Parel, has received its Occupancy Certificate. Possession handover ceremonies have started for early buyers.",
            "url": "https://economictimes.indiatimes.com/lodha-oc-1",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "source": "Economic Times",
        },
        {
            "headline": "Lodha Group IPO: Macrotech Developers lists at 10% premium",
            "summary": "Macrotech Developers, the developer behind Lodha brand, listed on BSE/NSE with a significant premium, buoyed by strong institutional interest.",
            "url": "https://livemint.com/lodha-ipo-1",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(),
            "source": "Livemint",
        },
    ],
    "Omkar Realtors & Developers Pvt Ltd": [
        {
            "headline": "Omkar Alta Monte homebuyers approach RERA as project stalls; 600+ families affected",
            "summary": "Homebuyers of Omkar Alta Monte in Malad East have filed complaints with MahaRERA alleging construction has halted despite full payment. Over 600 families are affected.",
            "url": "https://timesofindia.com/omkar-stall-1",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=12)).isoformat(),
            "source": "Times of India",
        },
        {
            "headline": "MahaRERA slaps ₹5 lakh penalty on Omkar Realtors for non-compliance",
            "summary": "MahaRERA has penalised Omkar Realtors for failing to submit quarterly project updates and misleading buyers about possession timelines.",
            "url": "https://hindustan-times.com/omkar-rera-penalty",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=25)).isoformat(),
            "source": "Hindustan Times",
        },
        {
            "headline": "Omkar debt restructuring talks with lenders collapse; insolvency threat looms",
            "summary": "Omkar Realtors is facing a financial crisis as debt restructuring talks with ICICI Bank and SBI have broken down. Analysts warn of potential NCLT proceedings.",
            "url": "https://business-standard.com/omkar-debt",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
            "source": "Business Standard",
        },
    ],
    "Housing Development & Infrastructure Ltd": [
        {
            "headline": "HDIL insolvency: NCLT approves resolution plan; buyers may get 22% of dues",
            "summary": "The National Company Law Tribunal has approved a resolution plan for HDIL under CIRP. Homebuyers' creditors committee estimates recovery of approximately 22 paise per rupee.",
            "url": "https://economictimes.com/hdil-nclt-resolution",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
            "source": "Economic Times",
        },
        {
            "headline": "HDIL PMC Bank fraud: CBI files chargesheet against Wadhawans",
            "summary": "The CBI has filed a chargesheet against HDIL promoters Rakesh and Sarang Wadhawan in connection with the Punjab & Maharashtra Co-operative Bank fraud case totalling ₹4,355 crore.",
            "url": "https://ndtv.com/hdil-pmcb-fraud",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            "source": "NDTV",
        },
    ],
    "DB Realty Ltd": [
        {
            "headline": "DB Realty's Sky Tower project remains stalled 5 years after promised delivery",
            "summary": "Buyers of DB Realty's Sky Tower project in Mira Road have been waiting over five years beyond the declared possession date. The RERA registration has since lapsed.",
            "url": "https://dnaindia.com/db-realty-stuck",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            "source": "DNA India",
        },
    ],
    "Nitesh Estates Ltd": [
        {
            "headline": "Nitesh Estates declared insolvent; IRP takes charge of operations",
            "summary": "The NCLT Bengaluru bench has admitted an insolvency petition against Nitesh Estates Ltd. An Insolvency Resolution Professional (IRP) has been appointed under the IBC.",
            "url": "https://businessline.com/nitesh-insolvency",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=18)).isoformat(),
            "source": "Business Line",
        },
    ],
    "Mantri Developers Pvt Ltd": [
        {
            "headline": "Mantri Serene buyers file case in NCDRC; project delayed by 5 years",
            "summary": "Over 200 homebuyers from Mantri Serene in Koramangala have approached the National Consumer Disputes Redressal Commission alleging a five-year delay and mis-selling.",
            "url": "https://deccanherald.com/mantri-ncdrc",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(),
            "source": "Deccan Herald",
        },
        {
            "headline": "Mantri developers under financial stress as lenders invoke pledged shares",
            "summary": "Multiple lenders have invoked pledged shares of Mantri Developers following default on repayment obligations. The company is seeking a one-time settlement.",
            "url": "https://mintcafe.com/mantri-pledge",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=35)).isoformat(),
            "source": "Mint",
        },
    ],
}


class NewsScraper(BaseScraper):
    """Fetches and analyses news about real estate developers and projects."""

    SOURCE_NAME = "news"
    _IS_DEV = settings.ENVIRONMENT.lower() == "development"

    async def scrape(self, query: str, **kwargs: Any) -> list[dict]:
        return await self.fetch_news(query)

    # ── Public API ────────────────────────────────────────────────────────────

    async def fetch_news(
        self,
        entity_name: str,
        is_developer: bool = True,
    ) -> list[dict]:
        """
        Fetch news articles for a developer or project name.
        Returns list of dicts: {headline, summary, url, published_at, source}.
        """
        if self._IS_DEV:
            self.log(f"[mock] fetch_news entity={entity_name}")
            articles = _MOCK_NEWS.get(entity_name, _MOCK_NEWS["default"])
            # Fill in template placeholders
            result = []
            for a in articles:
                result.append(
                    {
                        "headline": a["headline"].format(entity=entity_name),
                        "summary": a["summary"].format(entity=entity_name),
                        "url": a["url"],
                        "published_at": a["published_at"],
                        "source": a["source"],
                    }
                )
            return result

        articles: list[dict] = []

        if settings.NEWSAPI_KEY:
            articles.extend(await self._fetch_newsapi(entity_name))

        if not articles:
            articles.extend(await self._fetch_google_news_rss(entity_name))

        self.log(f"Fetched {len(articles)} articles for '{entity_name}'")
        return articles

    def analyze_sentiment(
        self,
        headline: str,
        summary: str,
    ) -> tuple[float, str, str]:
        """
        Keyword-based sentiment analysis.

        Returns (score, label, category):
          score    : float −1.0 to +1.0
          label    : 'positive' | 'neutral' | 'negative' | 'critical'
          category : 'nclt' | 'financial_stress' | 'delay' | 'fraud' |
                     'positive' | 'general'
        """
        text = f"{headline} {summary}".lower()

        negative_hits = [kw for kw in NEGATIVE_KEYWORDS if kw.lower() in text]
        positive_hits = [kw for kw in POSITIVE_KEYWORDS if kw.lower() in text]

        # Determine category from specific keyword clusters
        category = "general"
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw.lower() in text for kw in keywords):
                category = cat
                break

        # Severity: critical keywords override
        if any(kw.lower() in text for kw in ("nclt", "insolvency", "fraud", "bankrupt")):
            return -0.8, "critical", category

        n = len(negative_hits)
        p = len(positive_hits)

        if n >= 2:
            return -0.8, "critical", category
        if n == 1 and p == 0:
            return -0.4, "negative", category
        if p >= 1 and n == 0:
            return 0.6, "positive", "positive"
        return 0.1, "neutral", "general"

    async def scrape_and_store_news(
        self,
        developer: Developer,
        db: AsyncSession,
    ) -> int:
        """
        Fetch, analyse and persist news for a developer.
        Also updates ``developer.financial_stress_score`` based on recent
        negative coverage (blended with existing MCA-derived score).

        Returns count of NewsItem records created.
        """
        articles = await self.fetch_news(developer.name, is_developer=True)
        count = 0
        negative_score_acc = 0.0

        for article in articles:
            score, label, category = self.analyze_sentiment(
                article.get("headline", ""),
                article.get("summary", ""),
            )

            # Map label → SentimentLabel enum
            label_map = {
                "positive": SentimentLabel.positive,
                "neutral": SentimentLabel.neutral,
                "negative": SentimentLabel.negative,
                "critical": SentimentLabel.critical,
            }
            cat_map = {
                "nclt": NewsCategory.nclt,
                "financial_stress": NewsCategory.financial_stress,
                "delay": NewsCategory.delay,
                "fraud": NewsCategory.fraud,
                "positive": NewsCategory.positive,
                "general": NewsCategory.general,
            }

            # Parse published_at
            published_at: datetime | None = None
            if article.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(article["published_at"])
                except ValueError:
                    pass

            news_item = NewsItem(
                developer_id=developer.id,
                headline=article["headline"][:1024],
                summary=(article.get("summary") or "")[:4096],
                sentiment_score=score,
                sentiment_label=label_map.get(label, SentimentLabel.neutral),
                category=cat_map.get(category, NewsCategory.general),
                source_name=article.get("source"),
                source_url=article.get("url"),
                published_at=published_at,
            )
            db.add(news_item)
            count += 1

            if score < 0:
                # Accumulate negative signal — more recent = heavier weight
                age_days = 365
                if published_at:
                    age_days = max(1, (datetime.now(timezone.utc) - published_at).days)
                weight = max(0.1, 1.0 - age_days / 365.0)
                negative_score_acc += abs(score) * weight * 100

        # Update developer financial stress based on news
        if count > 0 and negative_score_acc > 0:
            news_stress_contribution = min(40.0, negative_score_acc)
            existing = developer.financial_stress_score or 0.0
            # Blend: 70% existing (MCA-based) + 30% news signal
            developer.financial_stress_score = min(
                100.0, existing * 0.70 + news_stress_contribution * 0.30
            )

        await db.commit()
        self.log(f"Stored {count} news items for {developer.name}")
        return count

    async def save(self, records: list[dict], db: Any) -> int:
        # Lightweight save path used by pipeline when developer is unknown
        count = 0
        for record in records:
            score, label, category = self.analyze_sentiment(
                record.get("headline", ""),
                record.get("summary", ""),
            )
            db.add(
                NewsItem(
                    headline=record.get("headline", "")[:1024],
                    summary=(record.get("summary") or "")[:4096],
                    sentiment_score=score,
                    sentiment_label=SentimentLabel(label),
                    category=NewsCategory(category),
                    source_name=record.get("source"),
                    source_url=record.get("url"),
                )
            )
            count += 1
        await db.commit()
        return count

    # ── Live fetch helpers ────────────────────────────────────────────────────

    async def _fetch_newsapi(self, entity_name: str) -> list[dict]:
        """Fetch from newsapi.org/v2/everything."""
        from_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f'"{entity_name}" real estate India',
            "from": from_date,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 50,
            "apiKey": settings.NEWSAPI_KEY,
        }
        # Build query string manually since fetch_page doesn't do params
        qs = urllib.parse.urlencode(params)
        html = await self.fetch_page(f"{url}?{qs}")

        import json
        try:
            data = json.loads(html)
        except Exception:
            return []

        return [
            {
                "headline": a.get("title", ""),
                "summary": a.get("description") or a.get("content") or "",
                "url": a.get("url", ""),
                "published_at": a.get("publishedAt", ""),
                "source": a.get("source", {}).get("name", ""),
            }
            for a in data.get("articles", [])
            if a.get("title")
        ]

    async def _fetch_google_news_rss(self, entity_name: str) -> list[dict]:
        """
        Fallback: scrape Google News RSS for the entity.
        Returns at most 10 articles.
        """
        encoded = urllib.parse.quote(f"{entity_name} real estate India")
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            html = await self.fetch_page(rss_url)
        except Exception as exc:
            self.log(f"Google News RSS fetch failed: {exc}", level="warning")
            return []

        soup = self.parse_html(html)
        articles = []
        for item in soup.find_all("item")[:10]:
            articles.append(
                {
                    "headline": self.extract_text(item.find("title")),
                    "summary": self.extract_text(item.find("description")),
                    "url": self.extract_text(item.find("link")),
                    "published_at": self.extract_text(item.find("pubdate")),
                    "source": "Google News",
                }
            )

        # Strip Google redirect wrappers from URLs
        for a in articles:
            m = re.search(r'url=([^&"]+)', a.get("url", ""))
            if m:
                a["url"] = urllib.parse.unquote(m.group(1))

        return articles
