"""
WhatSay AI Recommendation Engine

STRICT RULES (non-negotiable):
  1. NEVER let GPT invent products, prices, ASINs, or ratings
  2. ALWAYS require real Amazon search results before showing recommendations
  3. If no search API is configured → return clear error, not hallucinated data
  4. Affiliate links: /dp/ASIN?tag=... when ASIN exists, /s?k=...&tag=... otherwise

Data flow:
  Step 1 — Intent (GPT-4o): question → search queries + category + budget
  Step 2 — Search (SerpAPI PRIMARY): real Amazon India products with live data
             PA-API: future upgrade after Associates qualification
             No API: return "search unavailable" error — NO GPT fallback
  Step 3 — Recommend (GPT-4o): analyzes REAL products → verdict + ranking

SerpAPI is the ONLY product source for MVP.
PA-API is the future upgrade path.
GPT never generates product data.
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

Examples:
Q: "Best earbuds under 5000 for gym"
→ {"search_queries": ["wireless earbuds under 5000", "sports earbuds waterproof gym"], "budget_inr": 5000, "category": "audio"}

Q: "Should I buy iPhone 15?"
→ {"search_queries": ["Apple iPhone 15 128GB", "Apple iPhone 15"], "category": "smartphones"}

Q: "Should I buy Tata Nexon?"
→ {"is_amazon_supported": false, "unsupported_reason": "Cars and automobiles are not available on Amazon India."}"""

# ─── Step 3: Recommendation from REAL products ───────────────────────────────
RECOMMENDATION_PROMPT = """You are WhatSay AI — an honest Amazon India buying advisor.

USER QUESTION: {question}
BUDGET: {budget}

REAL AMAZON INDIA PRODUCTS (fetched live from Amazon search):
{products_context}

Analyze ONLY these real products. Do NOT invent or add any products not in the list.
Be specific, honest, and mention actual product names and prices from the list.

Return ONLY valid JSON:
{{
  "verdict": "highly_recommended|recommended|neutral|not_recommended|avoid",
  "summary": "2-3 sentence summary mentioning specific product names and prices from the list",
  "detailed_analysis": "Detailed paragraph with specific reasons referencing actual products above",
  "pros": ["specific pro mentioning product name", "pro 2", "pro 3"],
  "cons": ["specific con 1", "con 2"],
  "score": 85,
  "confidence": 92,
  "ranked_asins": [
    {{
      "asin": "EXACT_ASIN_FROM_LIST_ABOVE",
      "rank": 1,
      "why_recommended": "Specific reason this product fits the user's exact needs"
    }}
  ]
}}

IMPORTANT: ranked_asins must only contain ASINs from the product list above.
Do NOT add products that are not in the list."""


class RecommendationEngine:
    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider
        self.serp_client = self._init_serp()
        self.paapi_client = self._init_paapi()

    def _init_serp(self):
        """Initialize SerpAPI — PRIMARY product source for MVP."""
        key = getattr(settings, "SERPAPI_KEY", None)
        if key:
            from app.amazon.serp_search import SerpAPIAmazonSearch
            logger.info("✅ SerpAPI active — real Amazon India search enabled")
            return SerpAPIAmazonSearch(api_key=key, affiliate_tag=settings.AMAZON_AFFILIATE_TAG)
        logger.warning("⚠️  SERPAPI_KEY not set — product search unavailable")
        return None

    def _init_paapi(self):
        """Initialize PA-API — future upgrade after Associates qualification."""
        access_key = getattr(settings, "AMAZON_ACCESS_KEY", None)
        secret_key = getattr(settings, "AMAZON_SECRET_KEY", None)
        if access_key and secret_key:
            from app.amazon.paapi import AmazonPAAPI
            logger.info("✅ Amazon PA-API active")
            return AmazonPAAPI(access_key, secret_key, settings.AMAZON_AFFILIATE_TAG)
        return None

    def _search_available(self) -> bool:
        """Check if any real Amazon search API is configured."""
        return self.serp_client is not None or self.paapi_client is not None

    async def generate_recommendation(
        self,
        question: str,
        budget: Optional[int] = None,
        currency: str = "INR",
        affiliate_tag: str = "whatsay-21",
    ) -> RecommendationResult:
        """
        Full recommendation flow.
        REQUIRES real Amazon search API — never uses GPT to invent products.
        """

        # ── Check unsupported categories ──────────────────────────────────────
        q_lower = question.lower()
        for keyword in UNSUPPORTED_KEYWORDS:
            if keyword in q_lower:
                return self._unsupported_result(
                    f"'{keyword.title()}' products are not available on Amazon India. "
                    "WhatSay supports electronics, gadgets, appliances, and accessories."
                )

        # ── CRITICAL: Require real search API ─────────────────────────────────
        if not self._search_available():
            return self._search_unavailable_result()

        # ── Step 1: Extract intent ────────────────────────────────────────────
        intent = await self._extract_intent(question, budget)

        if not intent.get("is_amazon_supported", True):
            return self._unsupported_result(
                intent.get("unsupported_reason", "This category is not available on Amazon India.")
            )

        search_queries = intent.get("search_queries", [question])
        budget_inr = intent.get("budget_inr") or budget
        category = intent.get("category", "other")

        # ── Step 2: Search Amazon India for REAL products ─────────────────────
        amazon_products = await self._search_amazon(
            queries=search_queries,
            budget=budget_inr,
            affiliate_tag=affiliate_tag,
        )

        # No products found — do NOT fall back to GPT
        if not amazon_products:
            return self._no_products_result(category, intent.get("intent", "find_best"))

        logger.info("Real Amazon products fetched", count=len(amazon_products))

        # ── Step 3: GPT-4o analyzes REAL products ─────────────────────────────
        return await self._recommend_from_real_products(
            question=question,
            budget=budget_inr,
            amazon_products=amazon_products,
            category=category,
            intent=intent,
            affiliate_tag=affiliate_tag,
        )

    async def _extract_intent(self, question: str, budget: Optional[int]) -> dict:
        """Step 1: GPT-4o extracts search intent only — no product generation."""
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

    async def _search_amazon(
        self,
        queries: list[str],
        budget: Optional[int],
        affiliate_tag: str,
    ) -> list[dict]:
        """
        Step 2: Search Amazon India for REAL products.
        SerpAPI is primary. PA-API is future upgrade.
        Returns empty list if no results — never invents products.
        """

        # ── SerpAPI (Primary for MVP) ─────────────────────────────────────────
        if self.serp_client:
            try:
                products = await self.serp_client.search_multiple(
                    queries=queries,
                    max_per_query=4,
                    budget=budget,
                )
                if products:
                    return [self._serp_to_dict(p, affiliate_tag) for p in products]
            except Exception as e:
                logger.error("SerpAPI search failed", error=str(e))

        # ── PA-API (Future upgrade) ───────────────────────────────────────────
        if self.paapi_client:
            try:
                all_products = []
                seen_asins = set()
                for query in queries[:2]:
                    items = await self.paapi_client.search_items(
                        keywords=query,
                        item_count=4,
                        max_price=int(budget * 1.15) if budget else None,
                    )
                    for p in items:
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
                                # Direct product URL with affiliate tag
                                "affiliate_url": f"https://www.amazon.in/dp/{p.asin}?tag={affiliate_tag}",
                                "specs": {},
                                "source": "paapi",
                            })
                if all_products:
                    return all_products[:6]
            except Exception as e:
                logger.error("PA-API search failed", error=str(e))

        return []

    def _serp_to_dict(self, product, affiliate_tag: str) -> dict:
        """
        Convert SerpAPI product to dict with correct affiliate URL.
        - Has ASIN → direct /dp/ASIN?tag=... link (exact product page)
        - No ASIN → search /s?k=NAME&tag=... link (always works)
        """
        asin = getattr(product, "asin", None)
        name = getattr(product, "name", "")

        if asin:
            # Real ASIN from Amazon — direct product page
            amazon_url = f"https://www.amazon.in/dp/{asin}"
            affiliate_url = f"{amazon_url}?tag={affiliate_tag}"
        else:
            # No ASIN — use search URL (still tracks affiliate)
            encoded = quote_plus(name)
            amazon_url = f"https://www.amazon.in/s?k={encoded}"
            affiliate_url = f"{amazon_url}&tag={affiliate_tag}"

        return {
            "asin": asin,
            "name": name,
            "brand": getattr(product, "brand", ""),
            "price": getattr(product, "price", 0),
            "currency": "INR",
            "rating": getattr(product, "rating", 0),
            "review_count": getattr(product, "review_count", 0),
            "image_url": getattr(product, "image_url", None),
            "amazon_url": amazon_url,
            "affiliate_url": affiliate_url,
            "specs": {},
            "source": "serpapi",
        }

    async def _recommend_from_real_products(
        self,
        question: str,
        budget: Optional[int],
        amazon_products: list[dict],
        category: str,
        intent: dict,
        affiliate_tag: str,
    ) -> RecommendationResult:
        """Step 3: GPT-4o analyzes REAL Amazon products and ranks them."""

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
        except Exception as e:
            logger.error("AI recommendation failed", error=str(e))
            # Return products without AI ranking — still real data
            return self._build_unranked_result(amazon_products, category, intent)

        # Map ranked ASINs back to real product data
        asin_map = {p["asin"]: p for p in amazon_products if p.get("asin")}
        products_out = []

        for rp in rec_data.get("ranked_asins", []):
            asin = rp.get("asin", "")
            product = asin_map.get(asin)
            if not product:
                continue  # Skip — only use products from real search results

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
                "affiliate_url": product["affiliate_url"],  # Correct URL already set
                "asin": asin,
                "specs": product.get("specs", {}),
                "why_recommended": rp.get("why_recommended", ""),
                "rank": rp.get("rank", len(products_out) + 1),
                "is_alternative": False,
            })

        # If AI ranking failed, use all real products in search order
        if not products_out:
            return self._build_unranked_result(amazon_products, category, intent)

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

    def _format_products_context(self, products: list[dict]) -> str:
        """Format real Amazon products for GPT-4o context."""
        lines = []
        for i, p in enumerate(products[:6], 1):
            price_str = f"₹{p['price']:,.0f}" if p.get("price", 0) > 0 else "Price not listed"
            rating_str = (
                f"{p['rating']}/5 ({p['review_count']:,} reviews)"
                if p.get("rating", 0) > 0
                else "No ratings yet"
            )
            lines.append(
                f"{i}. ASIN: {p.get('asin', 'N/A')}\n"
                f"   Name: {p['name']}\n"
                f"   Brand: {p.get('brand', 'Unknown')}\n"
                f"   Price: {price_str}\n"
                f"   Rating: {rating_str}\n"
                f"   URL: {p.get('amazon_url', '')}"
            )
        return "\n\n".join(lines)

    def _build_unranked_result(
        self, products: list[dict], category: str, intent: dict
    ) -> RecommendationResult:
        """Return real products without AI ranking when GPT analysis fails."""
        products_out = [
            {
                **p,
                "category": category,
                "is_alternative": False,
                "why_recommended": "",
                "rank": i + 1,
            }
            for i, p in enumerate(products[:4])
        ]
        return RecommendationResult(
            verdict="recommended",
            summary=f"Found {len(products_out)} products on Amazon India matching your query.",
            detailed_analysis="",
            pros=["Available on Amazon India", "Real-time pricing"],
            cons=[],
            score=70,
            confidence=60,
            products=products_out,
            alternatives=[],
            category=category,
            intent=intent.get("intent", "find_best"),
            amazon_available=True,
        )

    # ─── Error results ────────────────────────────────────────────────────────

    def _search_unavailable_result(self) -> RecommendationResult:
        """
        Returned when no search API is configured.
        NEVER fall back to GPT-invented products.
        """
        return RecommendationResult(
            verdict="neutral",
            summary=(
                "Live Amazon product search is currently unavailable. "
                "Please configure SerpAPI to enable real product recommendations."
            ),
            detailed_analysis=(
                "WhatSay requires a live Amazon India product search to generate recommendations. "
                "This ensures every recommendation is based on real products with real prices — "
                "never AI-invented data. "
                "To enable: add SERPAPI_KEY to your environment variables. "
                "Sign up free at serpapi.com (100 searches/month free tier)."
            ),
            pros=[],
            cons=[],
            score=0,
            confidence=0,
            products=[],
            alternatives=[],
            category="other",
            intent="find_best",
            amazon_available=False,
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

    def _no_products_result(self, category: str, intent: str) -> RecommendationResult:
        """Returned when Amazon search returns no results — never invent products."""
        return RecommendationResult(
            verdict="neutral",
            summary=(
                "No matching products found on Amazon India for your query. "
                "Try a more specific product name or different keywords."
            ),
            detailed_analysis=(
                "Our live Amazon India search did not return results for this query. "
                "This may be because the product is out of stock, not available in India, "
                "or the search terms need to be more specific. "
                "Try searching with the exact product model number."
            ),
            pros=[], cons=[], score=0, confidence=80,
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
        """Stream brief intro while full recommendation loads."""
        if not self._search_available():
            yield "Live Amazon product search is unavailable. Please configure SerpAPI."
            return

        messages = [
            AIMessage(role="system", content=(
                "You are WhatSay AI, a friendly Amazon India buying advisor. "
                "Give a brief 1-2 sentence response saying you're searching Amazon India live "
                "for real products. Be warm and concise."
            )),
            AIMessage(role="user", content=question),
        ]
        async for chunk in self.ai_provider.stream(
            messages=messages, max_tokens=60, temperature=0.5
        ):
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
