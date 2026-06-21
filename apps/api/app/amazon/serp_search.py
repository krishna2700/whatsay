"""
Amazon India Product Search via SerpAPI

SerpAPI searches Amazon India in real-time and returns:
- Real product names exactly as on Amazon
- Real ASINs (verified, working)
- Real current prices
- Real ratings and review counts  
- Real product images
- Real product URLs → we append ?tag=whatsay-21

This is the CORRECT way to get live Amazon data without PA-API.

Setup:
  1. Sign up at https://serpapi.com (free tier: 100 searches/month)
  2. Get your API key from dashboard
  3. Add to .env: SERPAPI_KEY=your_key_here

SerpAPI pricing:
  - Free: 100 searches/month
  - Hobby: $50/month → 5,000 searches
  - Business: $130/month → 15,000 searches
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus
import httpx
import structlog

logger = structlog.get_logger()

SERPAPI_ENDPOINT = "https://serpapi.com/search"


@dataclass
class AmazonProduct:
    """Real Amazon India product from live search."""
    asin: str
    name: str
    brand: str
    price: float
    currency: str = "INR"
    rating: float = 0.0
    review_count: int = 0
    image_url: Optional[str] = None
    amazon_url: str = ""
    affiliate_url: str = ""
    is_prime: bool = False
    specs: dict = field(default_factory=dict)
    source: str = "serpapi"  # Track data source


class SerpAPIAmazonSearch:
    """
    Real Amazon India product search using SerpAPI.
    Returns live products with verified ASINs.
    """

    def __init__(self, api_key: str, affiliate_tag: str = "whatsay-21"):
        self.api_key = api_key
        self.affiliate_tag = affiliate_tag

    async def search(
        self,
        query: str,
        max_results: int = 5,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> list[AmazonProduct]:
        """
        Search Amazon India for real products.
        Returns products with real ASINs and affiliate links.
        """
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.in",
            "k": query,
            "api_key": self.api_key,
            "gl": "in",
            "hl": "en",
        }

        if min_price:
            params["low-price"] = str(min_price)
        if max_price:
            params["high-price"] = str(max_price)

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(SERPAPI_ENDPOINT, params=params)

            if response.status_code != 200:
                logger.error("SerpAPI error", status=response.status_code, body=response.text[:300])
                return []

            data = response.json()

            # Check for API errors
            if "error" in data:
                logger.error("SerpAPI returned error", error=data["error"])
                return []

            return self._parse_results(data, max_results)

        except Exception as e:
            logger.error("SerpAPI search failed", query=query, error=str(e))
            return []

    async def search_multiple(
        self,
        queries: list[str],
        max_per_query: int = 4,
        budget: Optional[int] = None,
    ) -> list[AmazonProduct]:
        """Search multiple queries and deduplicate by ASIN."""
        all_products: list[AmazonProduct] = []
        seen_asins: set[str] = set()

        # Run searches concurrently
        tasks = [
            self.search(
                query=q,
                max_results=max_per_query,
                max_price=int(budget * 1.2) if budget else None,
            )
            for q in queries[:3]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                for product in result:
                    if product.asin and product.asin not in seen_asins:
                        seen_asins.add(product.asin)
                        all_products.append(product)

        # Filter by budget if specified
        if budget and all_products:
            within_budget = [p for p in all_products if 0 < p.price <= budget * 1.15]
            if within_budget:
                all_products = within_budget

        # Sort by rating × review_count (best products first)
        all_products.sort(
            key=lambda p: (p.rating * min(p.review_count, 100000)),
            reverse=True,
        )

        logger.info(
            "SerpAPI search complete",
            queries=len(queries),
            products_found=len(all_products),
        )
        return all_products[:8]

    def _parse_results(self, data: dict, max_results: int) -> list[AmazonProduct]:
        """Parse SerpAPI Amazon response into AmazonProduct objects."""
        products = []

        # SerpAPI returns organic_results for Amazon
        items = data.get("organic_results", [])

        for item in items[:max_results]:
            try:
                asin = item.get("asin", "")
                if not asin:
                    continue

                # Product name
                name = item.get("title", "")
                if not name:
                    continue

                # Price — SerpAPI returns price as string like "₹3,999"
                price = 0.0
                price_data = item.get("price")
                if price_data:
                    if isinstance(price_data, (int, float)):
                        price = float(price_data)
                    elif isinstance(price_data, str):
                        # Remove ₹, commas, spaces
                        cleaned = price_data.replace("₹", "").replace(",", "").strip()
                        try:
                            price = float(cleaned)
                        except ValueError:
                            pass

                # Also try extracted_price
                if price == 0:
                    extracted = item.get("extracted_price", 0)
                    if extracted:
                        price = float(extracted)

                # Rating
                rating = 0.0
                rating_data = item.get("rating")
                if rating_data:
                    try:
                        rating = float(rating_data)
                    except (ValueError, TypeError):
                        pass

                # Review count
                review_count = 0
                reviews_data = item.get("reviews")
                if reviews_data:
                    try:
                        # Could be "45,231" or 45231
                        if isinstance(reviews_data, str):
                            review_count = int(reviews_data.replace(",", "").strip())
                        else:
                            review_count = int(reviews_data)
                    except (ValueError, TypeError):
                        pass

                # Image
                image_url = item.get("thumbnail") or item.get("image")

                # Prime
                is_prime = item.get("is_prime", False)

                # Brand — extract from title or dedicated field
                brand = item.get("brand", "")
                if not brand:
                    brand = self._extract_brand(name)

                # Build URLs
                amazon_url = f"https://www.amazon.in/dp/{asin}"
                affiliate_url = f"{amazon_url}?tag={self.affiliate_tag}"

                products.append(AmazonProduct(
                    asin=asin,
                    name=name,
                    brand=brand,
                    price=price,
                    currency="INR",
                    rating=rating,
                    review_count=review_count,
                    image_url=image_url,
                    amazon_url=amazon_url,
                    affiliate_url=affiliate_url,
                    is_prime=is_prime,
                    source="serpapi",
                ))

            except Exception as e:
                logger.warning("Failed to parse SerpAPI product", error=str(e))
                continue

        return products

    def _extract_brand(self, name: str) -> str:
        """Extract brand from product name."""
        known_brands = [
            "Apple", "Samsung", "OnePlus", "Xiaomi", "Redmi", "Realme",
            "OPPO", "Vivo", "Sony", "LG", "Motorola", "Nokia", "Google",
            "Asus", "ASUS", "Lenovo", "HP", "Dell", "Acer", "MSI",
            "JBL", "boAt", "Noise", "Bose", "Sennheiser", "Jabra",
            "Canon", "Nikon", "Fujifilm", "GoPro", "Logitech",
            "Anker", "Belkin", "Philips", "Panasonic", "Whirlpool",
        ]
        name_lower = name.lower()
        for brand in known_brands:
            if brand.lower() in name_lower:
                return brand
        return name.split()[0] if name else ""
