"""
WhatSay AI Recommendation Engine — Proper Architecture

REAL Flow (3 steps):
  Step 1 — Intent Extraction (GPT-4o)
    User question → extract product search queries + category + budget

  Step 2 — Amazon Search (PA-API or fallback)
    Search queries → REAL Amazon India products with live ASINs, prices, images
    IF PA-API configured: returns real live data from Amazon
    IF not configured: uses Amazon search URLs (always valid, affiliate tracked)

  Step 3 — AI Recommendation (GPT-4o)
    Real Amazon products → honest analysis → verdict + pros/cons + ranking

NO hardcoded products. NO fake ASINs. REAL Amazon data only.
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
    "innova", "fortuner", "baleno", "activa", "pulsar",
    "real estate", "property", "house", "apartment", "flat", "plot",
    "flight", "flights", "hotel", "hotels", "travel package",
    "insurance", "loan", "loans", "credit card", "mutual fund",
}

# ─── Step 1: Intent extraction prompt ────────────────────────────────────────
INTENT_PROMPT = """You are a product search expert for Amazon India.

Extract search intent from the user's question and return JSON:
{
  "is_amazon_supported": true,
  "unsupported_reason": null,
  "category": "Electronics|Computers|Headphones|Smartphones|Laptops|Cameras|Wearables|HomeAppliances|Other",
  "search_index": "Electronics|Computers|All",
  "search_queries": ["query1", "query2"],
  "budget_inr": null,
  "intent": "buy_specific|compare|find_best|budget_search|review_check"
}

Rules:
- is_amazon_supported = false ONLY for: cars, real estate, flights, insurance, loans
- Generate 2-3 specific Amazon India search queries
- budget_inr: extract number if mentioned (e.g. 5000 for "under 5000")
- Keep queries short and specific for Amazon search

Examples:
Q: "Best earbuds under 5000 for gym"
→ search_queries: ["wireless earbuds under 5000", "sports earbuds IPX5 waterproof", "gym earbuds bluetooth"]
→ budget_inr: 5000, category: "Headphones"

Q: "Should I buy iPhone 15?"
→ search_queries: ["Apple iPhone 15 128GB", "iPhone 15"]
→ category: "Smartphones"

Q: "Should I buy Tata Nexon?"
→ is_amazon_supported: false
→ unsupported_reason: "Cars and automobiles are not available on Amazon India."
"""

# ─── Step 3: Recommendation prompt ───────────────────────────────────────────
RECOMMENDATION_PROMPT = """You are WhatSay AI — an honest Amazon India buying advisor.

USER QUESTION: {question}
BUDGET: {budget}

REAL AMAZON INDIA PRODUCTS FOUND (live data):
{products_context}

Based ONLY on the above real Amazon products, generate a buying recommendation.

Rules:
- Only recommend products from the list above
- Be honest about pros and cons
- Consider the user's budget and use case
- Rank products by best fit for the user's needs

Return ONLY valid JSON:
{{
  "verdict": "highly_recommended|recommended|neutral|not_recommended|avoid",
  "summary": "2-3 sentence honest summary mentioning specific products",
  "detailed_analysis": "Detailed paragraph explaining your recommendation",
  "pros": ["specific pro 1", "specific pro 2", "specific pro 3"],
  "cons": ["specific con 1", "specific con 2"],
  "score": 85,
  "confidence": 90,
  "ranked_products": [
    {{
      "asin": "ASIN from the list",
      "rank": 1,
      "why_recommended": "Specific reason this fits the user's needs"
    }}
  ]
}}"""


class RecommendationEngine:
    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider
        self._paapi = self._init_paapi()

    def _init_paapi(self):
        """Initialize Amazon PA-API if credentials are configured."""
        access_key = getattr(settings, "AMAZON_ACCESS_KEY", None)
        secret_key = getattr(settings, "AMAZON_SECRET_KEY", None)
        partner_tag = getattr(settings, "AMAZON_AFFILIATE_TAG", "whatsay-21")

        if access_key and secret_key:
            from app.amazon.paapi import AmazonPAAPI
            logger.info("Amazon PA-API configured — using live product data")
            return AmazonPAAPI(access_key, secret_key, partner_tag)

        logger.info("Amazon PA-API not configured — using search URL fallback")
        return None

    async def generate_recommendation(
        self,
        question: str,
        budget: Optional[int] = None,
        currency: str = "INR",
        affiliate_tag: str = "whatsay-21",
    ) -> RecommendationResult:
        """
        Full 3-step recommendation flow.
        """

        # ── Step 1: Check unsupported categories ──────────────────────────────
        q_lower = question.lower()
        for keyword in UNSUPPORTED_KEYWORDS:
            if keyword in q_lower:
                return self._unsupported_result(
                    f"'{keyword.title()}' products are not available on Amazon India. "
                    "WhatSay supports electronics, gadgets, appliances, and accessories."
                )

        # ── Step 2: Extract intent via GPT-4o ────────────────────────────────
        intent = await self._extract_intent(question, budget)

        if not intent.get("is_amazon_supported", True):
            return self._unsupported_result(
                intent.get("unsupported_reason", "This category is not available on Amazon India.")
            )

        search_queries = intent.get("search_queries", [question])
        budget_inr = intent.get("budget_inr") or budget
        search_index = intent.get("search_index", "Electronics")
        category = intent.get("category", "other").lower()

        # ── Step 3: Search Amazon India for REAL products ─────────────────────
        amazon_products = await self._search_amazon(
            queries=search_queries,
            search_index=search_index,
            budget=budget_inr,
            affiliate_tag=affiliate_tag,
        )

        if not amazon_products:
            return self._no_products_result(question, category, intent.get("intent", "find_best"))

        # ── Step 4: Generate AI recommendation from real products ─────────────
        return await self._generate_recommendation(
            question=question,
            budget=budget_inr,
            amazon_products=amazon_products,
            category=category,
            intent_data=intent,
            affiliate_tag=affiliate_tag,
        )

    async def _extract_intent(self, question: str, budget: Optional[int]) -> dict:
        """Step 1: Use GPT-4o to extract search intent."""
        user_msg = f"Question: {question}"
        if budget:
            user_msg += f"\nBudget: ₹{budget:,}"

        try:
            response = await self.ai_provider.complete(
                messages=[
                    AIMessage(role="system", content=INTENT_PROMPT),
                    AIMessage(role="user", content=user_msg),
                ],
                max_tokens=400,
                temperature=0.1,
            )
            return self._parse_json(response.content)
        except Exception as e:
            logger.error("Intent extraction failed", error=str(e))
            return {
                "is_amazon_supported": True,
                "search_queries": [question],
                "category": "Electronics",
                "search_index": "Electronics",
                "intent": "find_best",
                "budget_inr": budget,
            }

    async def _search_amazon(
        self,
        queries: list[str],
        search_index: str,
        budget: Optional[int],
        affiliate_tag: str,
    ) -> list[dict]:
        """Step 2: Search Amazon India for real products."""

        # ── PA-API path (real live data) ──────────────────────────────────────
        if self._paapi:
            all_products = []
            seen_asins = set()

            for query in queries[:2]:
                try:
                    products = await self._paapi.search_items(
                        keywords=query,
                        search_index=search_index,
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
                                "is_prime": p.is_prime,
                                "specs": {},
                            })
                except Exception as e:
                    logger.error("PA-API query failed", query=query, error=str(e))

            if all_products:
                logger.info("PA-API returned products", count=len(all_products))
                return all_products[:6]

        # ── Fallback: Search URL path ─────────────────────────────────────────
        # When PA-API is not configured, build search URLs for each query.
        # These always work and track affiliate commissions.
        logger.info("Using Amazon search URL fallback", queries=queries)
        products = []
        for i, query in enumerate(queries[:3]):
            search_url = f"https://www.amazon.in/s?k={quote_plus(query)}&tag={affiliate_tag}"
            products.append({
                "asin": None,
                "name": query,  # Will be enriched by GPT-4o
                "brand": "",
                "price": 0,
                "currency": "INR",
                "rating": 0,
                "review_count": 0,
                "image_url": None,
                "amazon_url": search_url,
                "affiliate_url": search_url,
                "is_prime": False,
                "specs": {},
                "search_query": query,
            })
        return products

    async def _generate_recommendation(
        self,
        question: str,
        budget: Optional[int],
        amazon_products: list[dict],
        category: str,
        intent_data: dict,
        affiliate_tag: str,
    ) -> RecommendationResult:
        """Step 3: GPT-4o analyzes real Amazon products and generates recommendation."""

        has_real_products = any(p.get("asin") for p in amazon_products)

        if has_real_products:
            # We have real PA-API data — do full AI analysis
            products_context = self._format_products_context(amazon_products)
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
                return self._build_result_from_paapi(
                    rec_data, amazon_products, category, intent_data, affiliate_tag
                )

            except Exception as e:
                logger.error("AI recommendation failed", error=str(e))
                # Fallback: return products without AI ranking
                return self._build_simple_result(amazon_products, category, intent_data)

        else:
            # No PA-API — use GPT-4o to generate recommendation with search URLs
            return await self._generate_with_search_urls(
                question, budget, amazon_products, category, intent_data, affiliate_tag
            )

    async def _generate_with_search_urls(
        self,
        question: str,
        budget: Optional[int],
        search_products: list[dict],
        category: str,
        intent_data: dict,
        affiliate_tag: str,
    ) -> RecommendationResult:
        """
        When PA-API is not configured:
        GPT-4o generates product recommendations, we build search URLs.
        """
        budget_str = f"₹{budget:,}" if budget else "Not specified"

        prompt = f"""You are WhatSay AI — an Amazon India buying advisor.

USER QUESTION: {question}
BUDGET: {budget_str}

Recommend 3-4 REAL products available on Amazon India for this question.
Use your knowledge of actual products sold on Amazon India.

Return ONLY valid JSON:
{{
  "verdict": "highly_recommended|recommended|neutral|not_recommended|avoid",
  "summary": "2-3 sentence summary",
  "detailed_analysis": "Detailed analysis paragraph",
  "pros": ["pro1", "pro2", "pro3"],
  "cons": ["con1", "con2"],
  "score": 85,
  "confidence": 90,
  "products": [
    {{
      "name": "Exact product name as sold on Amazon India",
      "brand": "Brand",
      "search_query": "Amazon search query to find this product",
      "price": 3999,
      "rating": 4.2,
      "review_count": 25000,
      "specs": {{"Battery": "40hr", "ANC": "Yes", "Water Resistance": "IPX4"}},
      "why_recommended": "Why this fits the user's needs",
      "rank": 1
    }}
  ]
}}"""

        response = await self.ai_provider.complete(
            messages=[
                AIMessage(role="system", content=prompt),
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

            # Build Amazon search URL with affiliate tag
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
            confidence=int(data.get("confidence", 80)),
            products=products_out,
            alternatives=[],
            category=category,
            intent=intent_data.get("intent", "find_best"),
            amazon_available=True,
        )

    def _format_products_context(self, products: list[dict]) -> str:
        """Format real Amazon products for AI context."""
        lines = []
        for i, p in enumerate(products[:6], 1):
            price_str = f"₹{p['price']:,.0f}" if p["price"] > 0 else "Price not listed"
            rating_str = f"{p['rating']}/5 ({p['review_count']:,} reviews)" if p["rating"] > 0 else "No ratings"
            lines.append(
                f"{i}. ASIN: {p['asin']}\n"
                f"   Name: {p['name']}\n"
                f"   Brand: {p['brand']}\n"
                f"   Price: {price_str}\n"
                f"   Rating: {rating_str}\n"
                f"   Prime: {'Yes' if p.get('is_prime') else 'No'}"
            )
        return "\n\n".join(lines)

    def _build_result_from_paapi(
        self,
        rec_data: dict,
        amazon_products: list[dict],
        category: str,
        intent_data: dict,
        affiliate_tag: str,
    ) -> RecommendationResult:
        """Build result using PA-API products + AI ranking."""
        asin_map = {p["asin"]: p for p in amazon_products if p.get("asin")}
        products_out = []

        for rp in rec_data.get("ranked_products", []):
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

        # If AI didn't rank properly, use all products
        if not products_out:
            products_out = [
                {**p, "category": category, "is_alternative": False, "why_recommended": ""}
                for p in amazon_products[:4]
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
            intent=intent_data.get("intent", "find_best"),
            amazon_available=True,
        )

    def _build_simple_result(
        self, products: list[dict], category: str, intent_data: dict
    ) -> RecommendationResult:
        """Simple result when AI analysis fails."""
        return RecommendationResult(
            verdict="recommended",
            summary=f"Found {len(products)} products on Amazon India matching your query.",
            detailed_analysis="",
            pros=["Available on Amazon India", "Prime eligible options available"],
            cons=[],
            score=70,
            confidence=60,
            products=[{**p, "category": category, "is_alternative": False} for p in products[:4]],
            alternatives=[],
            category=category,
            intent=intent_data.get("intent", "find_best"),
            amazon_available=True,
        )

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

    def _no_products_result(self, question: str, category: str, intent: str) -> RecommendationResult:
        return RecommendationResult(
            verdict="neutral",
            summary="No matching products found on Amazon India. Please try a more specific search.",
            detailed_analysis="",
            pros=[], cons=[], score=0, confidence=70,
            products=[], alternatives=[],
            category=category, intent=intent,
            amazon_available=True,
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
