"""
WhatSay AI Recommendation Engine

REAL 3-Step Flow:
  Step 1 — Intent (GPT-4o): question → search queries + category + budget
  Step 2 — Search (SerpAPI): queries → REAL Amazon India products (live ASINs, prices, images)
  Step 3 — Recommend (GPT-4o): real products → honest verdict + pros/cons + ranking

Data sources (priority order):
  1. SerpAPI → real live Amazon India search (configure SERPAPI_KEY)
  2. Amazon PA-API → official Amazon API (configure AMAZON_ACCESS_KEY + AMAZON_SECRET_KEY)
  3. Fallback → GPT-4o knowledge + Amazon search URLs (no API key needed)

Affiliate links:
  - With SerpAPI/PA-API: https://www.amazon.in/dp/REAL_ASIN?tag=whatsay-21
  - Fallback: https://www.amazon.in/s?k=PRODUCT+NAME&tag=whatsay-21
"""

import json
import re
from typing import Optional, AsyncGenerator
from urllib.parse import quote_plus
from app.ai.base import BaseAIProvider, AIMessage, RecommendationResult
from app.core.config import settings
import structlog

logger = structlog.get_logger()

# ─── Unsupported categories ───────────────────────────────────────────────────
UNSUPPORTED_KEYWORDS = {
    "car", "cars", "automobile", "automobiles", "vehicle", "vehicles",
    "bike", "motorcycle", "scooter", "nexon", "swift", "creta",
    "innova", "fortuner", "baleno", "activa", "pulsar", "tata nexon",
    "real estate", "property", "house", "apartment", "flat", "plot",
    "flight", "flights", "hotel", "hotels", "travel package",
    "insurance", "loan", "loans", "credit card", "mutual fund",
}

# ─── Step 1: Intent extraction ────────────────────────────────────────────────
INTENT_PROMPT = """You are a product search expert for Amazon India.

Extract search intent from the user's question. Return ONLY valid JSON:
{
  "is_amazon_supported": true,
  "unsupported_reason": null,
  "category": "audio|smartphones|laptops|cameras|wearables|tablets|appliances|accessories|other",
  "search_queries": ["specific amazon search query 1", "specific amazon search query 2"],
  "budget_inr": null,
  "intent": "buy_specific|compare|find_best|budget_search|review_check"
}

Rules:
- is_amazon_supported = false ONLY for: cars, real estate, flights, insurance, loans
- Generate 2-3 specific Amazon India search queries (short, keyword-focused)
- budget_inr: extract number if mentioned (5000 for "under ₹5,000")
- Queries should work well as Amazon search terms

Examples:
Q: "Best earbuds under 5000 for gym"
→ {"search_queries": ["wireless earbuds under 5000", "sports earbuds waterproof gym", "bluetooth earbuds IPX5"], "budget_inr": 5000, "category": "audio"}

Q: "Should I buy iPhone 15?"
→ {"search_queries": ["Apple iPhone 15 128GB", "Apple iPhone 15"], "category": "smartphones"}

Q: "Best laptop under 80000 for programming"
→ {"search_queries": ["laptop under 80000 programming", "developer laptop i7 16GB"], "budget_inr": 80000, "category": "laptops"}

Q: "Should I buy Tata Nexon?"
→ {"is_amazon_supported": false, "unsupported_reason": "Cars and automobiles are not available on Amazon India."}"""

# ─── Step 3: Recommendation from real products ────────────────────────────────
RECOMMENDATION_PROMPT = """You are WhatSay AI — an honest Amazon India buying advisor.

USER QUESTION: {question}
BUDGET: {budget}

REAL AMAZON INDIA PRODUCTS (live data from Amazon search):
{products_context}

Analyze these REAL products and generate a buying recommendation.
Only recommend products from the list above. Be specific and honest.

Return ONLY valid JSON:
{{
  "verdict": "highly_recommended|recommended|neutral|not_recommended|avoid",
  "summary": "2-3 sentence summary mentioning specific product names and prices",
  "detailed_analysis": "Detailed paragraph with specific reasons why these products suit the user",
  "pros": ["specific pro with product name", "specific pro 2", "specific pro 3"],
  "cons": ["specific con 1", "specific con 2"],
  "score": 85,
  "confidence": 92,
  "ranked_asins": [
    {{
      "asin": "ASIN_FROM_LIST",
      "rank": 1,
      "why_recommended": "Specific reason this product fits the user's exact needs"
    }}
  ]
}}"""

# ─── Fallback: GPT-4o generates products when no API ─────────────────────────
FALLBACK_PROMPT = """You are WhatSay AI — an Amazon India buying advisor.

USER QUESTION: {question}
BUDGET: {budget}

Recommend 3-4 REAL products available on Amazon India.
Use your knowledge of actual products sold on Amazon India right now.

Return ONLY valid JSON:
{{
  "verdict": "highly_recommended|recommended|neutral|not_recommended|avoid",
  "summary": "2-3 sentence summary with specific product names",
  "detailed_analysis": "Detailed analysis paragraph",
  "pros": ["pro1", "pro2", "pro3"],
  "cons": ["con1", "con2"],
  "score": 85,
  "confidence": 75,
  "products": [
    {{
      "name": "Exact product name as sold on Amazon India",
      "brand": "Brand name",
      "search_query": "Amazon search query to find this exact product",
      "price": 3999,
      "rating": 4.2,
      "review_count": 25000,
      "specs": {{"Battery": "40hr", "ANC": "Yes", "Water Resistance": "IPX4"}},
      "why_recommended": "Why this fits the user's specific needs",
      "rank": 1
    }}
  ]
}}"""


class RecommendationEngine:
    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider
        self.serp_client = self._init_serp()
        self.paapi_client = self._init_paapi()

    def _init_serp(self):
        """Initialize SerpAPI client if key is configured."""
        key = getattr(settings, "SERPAPI_KEY", None)
        if key:
            from app.amazon.serp_search import SerpAPIAmazonSearch
            logger.info("✅ SerpAPI configured — real Amazon India search active")
            return SerpAPIAmazonSearch(api_key=key, affiliate_tag=settings.AMAZON_AFFILIATE_TAG)
        logger.info("⚠️  SerpAPI not configured — using GPT-4o fallback")
        return None

    def _init_paapi(self):
        """Initialize Amazon PA-API if credentials configured."""
        access_key = getattr(settings, "AMAZON_ACCESS_KEY", None)
        secret_key = getattr(settings, "AMAZON_SECRET_KEY", None)
        if access_key and secret_key:
            from app.amazon.paapi import AmazonPAAPI
            logger.info("✅ Amazon PA-API configured")
            return AmazonPAAPI(access_key, secret_key, settings.AMAZON_AFFILIATE_TAG)
        return None

    async def generate_recommendation(
        self,
        question: str,
        budget: Optional[int] = None,
        currency: str = "INR",
        affiliate_tag: str = "whatsay-21",
    ) -> RecommendationResult:
        """Full recommendation flow."""

        # ── Quick unsupported category check ─────────────────────────────────
        q_lower = question.lower()
        for keyword in UNSUPPORTED_KEYWORDS:
            if keyword in q_lower:
                return self._unsupported_result(
                    f"'{keyword.title()}' products are not available on Amazon India. "
                    "WhatSay supports electronics, gadgets, appliances, and accessories."
                )

        # ── Step 1: Extract intent ────────────────────────────────────────────
        intent = await self._extract_intent(question, budget)

        if not intent.get("is_amazon_supported", True):
            return self._unsupported_result(
                intent.get("unsupported_reason", "This category is not available on Amazon India.")
            )

        search_queries = intent.get("search_queries", [question])
        budget_inr = intent.get("budget_inr") or budget
        category = intent.get("category", "other")

        # ── Step 2: Search Amazon India ───────────────────────────────────────
        if self.serp_client:
            # REAL search via SerpAPI
            amazon_products = await self.serp_client.search_multiple(
                queries=search_queries,
                max_per_query=4,
                budget=budget_inr,
            )
            if amazon_products:
                logger.info("SerpAPI products found", count=len(amazon_products))
                return await self._recommend_from_real_products(
                    question, budget_inr, amazon_products, category, intent, affiliate_tag
                )

        elif self.paapi_client:
            # REAL search via PA-API
            amazon_products = await self._search_paapi(search_queries, budget_inr)
            if amazon_products:
                return await self._recommend_from_real_products(
                    question, budget_inr, amazon_products, category, intent, affiliate_tag
                )

        # ── Fallback: GPT-4o knowledge + search URLs ──────────────────────────
        logger.info("Using GPT-4o fallback (no search API configured)")
        return await self._fallback_recommendation(
            question, budget_inr, category, intent, affiliate_tag
        )

    async def _extract_intent(self, question: str, budget: Optional[int]) -> dict:
        """Step 1: GPT-4o extracts search intent."""
        user_msg = f"Question: {question}"
        if budget:
            user_msg += f"\nBudget: ₹{budget:,}"
        try:
            response = await self.ai_provider.complete(
                messages=[
                    AIMessage(role="system", content=INTENT_PROMPT),
                    AIMessage(role="user", content=user_msg),
                ],
                max_tokens=300,
                temperature=0.1,
            )
            return self._parse_json(response.content)
        except Exception as e:
            logger.error("Intent extraction failed", error=str(e))
            return {
                "is_amazon_supported": True,
                "search_queries": [question],
                "category": "other",
                "intent": "find_best",
                "budget_inr": budget,
            }

    async def _search_paapi(self, queries: list[str], budget: Optional[int]) -> list[dict]:
        """Search via Amazon PA-API."""
        all_products = []
        seen_asins = set()
        for query in queries[:2]:
            try:
                products = await self.paapi_client.search_items(
                    keywords=query,
                    item_count=4,
                    max_price=int(budget * 1.15) if budget else None,
                )
                for p in products:
                    if p.asin not in seen_asins:
                        seen_asins.add(p.asin)
                        all_products.append({
                            "asin": p.asin,
                            "name": p.name,
                            "brand": p.brand,
                            "price": p.price,
                            "currency": "INR",
                            "rating": p.rating,
                            "review_count": p.review_count,
                            "image_url": p.image_url,
                            "amazon_url": p.amazon_url,
                            "affiliate_url": p.affiliate_url,
                            "specs": {},
                        })
            except Exception as e:
                logger.error("PA-API query failed", error=str(e))
        return all_products[:6]

    async def _recommend_from_real_products(
        self,
        question: str,
        budget: Optional[int],
        products: list,
        category: str,
        intent: dict,
        affiliate_tag: str,
    ) -> RecommendationResult:
        """Step 3: GPT-4o analyzes REAL Amazon products."""

        # Convert SerpAPI AmazonProduct objects to dicts if needed
        product_dicts = []
        for p in products:
            if hasattr(p, "asin"):
                product_dicts.append({
                    "asin": p.asin,
                    "name": p.name,
                    "brand": p.brand,
                    "price": p.price,
                    "currency": "INR",
                    "rating": p.rating,
                    "review_count": p.review_count,
                    "image_url": p.image_url,
                    "amazon_url": p.amazon_url,
                    "affiliate_url": f"https://www.amazon.in/dp/{p.asin}?tag={affiliate_tag}",
                    "specs": getattr(p, "specs", {}),
                })
            else:
                product_dicts.append(p)

        products_context = self._format_products_context(product_dicts)
        budget_str = f"₹{budget:,}" if budget else "Not specified"

        try:
            response = await self.ai_provider.complete(
                messages=[
                    AIMessage(
                        role="system",
                        content=RECOMMENDATION_PROMPT.format(
                            question=question,
                            budget=budget_str,
                            products_context=products_context,
                        ),
                    ),
                    AIMessage(role="user", content=question),
                ],
                max_tokens=2000,
                temperature=0.3,
            )
            rec_data = self._parse_json(response.content)
        except Exception as e:
            logger.error("AI recommendation failed", error=str(e))
            rec_data = {"verdict": "recommended", "summary": "", "pros": [], "cons": [], "score": 70, "confidence": 60}

        # Map ranked ASINs back to full product data
        asin_map = {p["asin"]: p for p in product_dicts if p.get("asin")}
        products_out = []

        for rp in rec_data.get("ranked_asins", []):
            asin = rp.get("asin", "")
            product = asin_map.get(asin)
            if not product:
                continue
            products_out.append({
                "name": product["name"],
                "brand": product["brand"],
                "category": category,
                "price": product["price"],
                "currency": "INR",
                "rating": product["rating"],
                "review_count": product["review_count"],
                "image_url": product.get("image_url"),
                "amazon_url": product["amazon_url"],
                "affiliate_url": product["affiliate_url"],
                "asin": asin,
                "specs": product.get("specs", {}),
                "why_recommended": rp.get("why_recommended", ""),
                "rank": rp.get("rank", len(products_out) + 1),
                "is_alternative": False,
            })

        # If AI didn't rank, use all products in order
        if not products_out:
            products_out = [
                {
                    **p,
                    "category": category,
                    "is_alternative": False,
                    "why_recommended": "",
                    "rank": i + 1,
                }
                for i, p in enumerate(product_dicts[:4])
            ]

        return RecommendationResult(
            verdict=rec_data.get("verdict", "recommended"),
            summary=rec_data.get("summary", ""),
            detailed_analysis=rec_data.get("detailed_analysis", ""),
            pros=rec_data.get("pros", []),
            cons=rec_data.get("cons", []),
            score=int(rec_data.get("score", 75)),
            confidence=int(rec_data.get("confidence", 80)),
            products=products_out,
            alternatives=[],
            category=category,
            intent=intent.get("intent", "find_best"),
            amazon_available=True,
        )

    async def _fallback_recommendation(
        self,
        question: str,
        budget: Optional[int],
        category: str,
        intent: dict,
        affiliate_tag: str,
    ) -> RecommendationResult:
        """Fallback when no search API is configured."""
        budget_str = f"₹{budget:,}" if budget else "Not specified"

        response = await self.ai_provider.complete(
            messages=[
                AIMessage(
                    role="system",
                    content=FALLBACK_PROMPT.format(question=question, budget=budget_str),
                ),
                AIMessage(role="user", content=question),
            ],
            max_tokens=2500,
            temperature=0.2,
        )

        data = self._parse_json(response.content)
        products_out = []

        for i, p in enumerate(data.get("products", [])):
            name = p.get("name", "")
            search_query = p.get("search_query", name)
            if not name:
                continue

            # Amazon search URL — always works, affiliate tracked
            affiliate_url = f"https://www.amazon.in/s?k={quote_plus(search_query)}&tag={affiliate_tag}"
            amazon_url = f"https://www.amazon.in/s?k={quote_plus(search_query)}"

            products_out.append({
                "name": name,
                "brand": p.get("brand", ""),
                "category": category,
                "price": float(p.get("price", 0)),
                "currency": "INR",
                "rating": float(p.get("rating", 0)),
                "review_count": int(p.get("review_count", 0)),
                "image_url": None,
                "amazon_url": amazon_url,
                "affiliate_url": affiliate_url,
                "asin": None,
                "specs": p.get("specs", {}),
                "why_recommended": p.get("why_recommended", ""),
                "rank": int(p.get("rank", i + 1)),
                "is_alternative": False,
            })

        return RecommendationResult(
            verdict=data.get("verdict", "recommended"),
            summary=data.get("summary", ""),
            detailed_analysis=data.get("detailed_analysis", ""),
            pros=data.get("pros", []),
            cons=data.get("cons", []),
            score=int(data.get("score", 75)),
            confidence=int(data.get("confidence", 75)),
            products=products_out,
            alternatives=[],
            category=category,
            intent=intent.get("intent", "find_best"),
            amazon_available=True,
        )

    def _format_products_context(self, products: list[dict]) -> str:
        lines = []
        for i, p in enumerate(products[:6], 1):
            price_str = f"₹{p['price']:,.0f}" if p.get("price", 0) > 0 else "Price not listed"
            rating_str = f"{p['rating']}/5 ({p['review_count']:,} reviews)" if p.get("rating", 0) > 0 else "No ratings yet"
            lines.append(
                f"{i}. ASIN: {p.get('asin', 'N/A')}\n"
                f"   Name: {p['name']}\n"
                f"   Brand: {p.get('brand', 'Unknown')}\n"
                f"   Price: {price_str}\n"
                f"   Rating: {rating_str}\n"
                f"   URL: {p.get('amazon_url', '')}"
            )
        return "\n\n".join(lines)

    def _unsupported_result(self, reason: str) -> RecommendationResult:
        return RecommendationResult(
            verdict="neutral",
            summary=reason,
            detailed_analysis=(
                "WhatSay supports product recommendations for items available on Amazon India — "
                "electronics, gadgets, appliances, and accessories. "
                "Automobiles, real estate, and financial services are not supported."
            ),
            pros=[], cons=[], score=0, confidence=100,
            products=[], alternatives=[],
            category="other", intent="find_best",
            amazon_available=False,
        )

    async def stream_recommendation(
        self,
        question: str,
        budget: Optional[int] = None,
        currency: str = "INR",
        affiliate_tag: str = "whatsay-21",
    ) -> AsyncGenerator[str, None]:
        messages = [
            AIMessage(role="system", content=(
                "You are WhatSay AI, a friendly Amazon India buying advisor. "
                "Give a brief 1-2 sentence response saying you're searching Amazon India "
                "for the best options. Be warm and concise."
            )),
            AIMessage(role="user", content=question),
        ]
        async for chunk in self.ai_provider.stream(messages=messages, max_tokens=60, temperature=0.5):
            yield chunk

    def _parse_json(self, content: str) -> dict:
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return json.loads(content)
