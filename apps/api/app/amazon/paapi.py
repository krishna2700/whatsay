"""
Amazon Product Advertising API (PA-API 5.0) Integration

Official Amazon API — returns REAL products with:
- Real ASINs
- Real current prices  
- Real ratings & review counts
- Real product images
- Real product titles

Setup required:
1. Join Amazon Associates India: https://affiliate-program.amazon.in/
2. After making qualifying sales, request PA-API access
3. Get: AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG

Until PA-API credentials are available, we use the intelligent fallback:
- Real Amazon search URLs that always work
- GPT-4o for product analysis
"""

import hashlib
import hmac
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import quote_plus
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class AmazonProduct:
    asin: str
    name: str
    brand: str
    price: float
    currency: str
    rating: float
    review_count: int
    image_url: Optional[str]
    amazon_url: str
    affiliate_url: str
    category: str
    specs: dict = field(default_factory=dict)
    is_prime: bool = False


class AmazonPAAPI:
    """
    Amazon Product Advertising API 5.0 client.
    Supports Amazon India (www.amazon.in).
    """

    HOST = "webservices.amazon.in"
    REGION = "eu-west-1"
    SERVICE = "ProductAdvertisingAPI"
    ENDPOINT = f"https://{HOST}/paapi5/searchitems"

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        partner_tag: str,
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.partner_tag = partner_tag

    async def search_items(
        self,
        keywords: str,
        search_index: str = "Electronics",
        item_count: int = 5,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> list[AmazonProduct]:
        """Search Amazon India for products."""

        payload = {
            "Keywords": keywords,
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.in",
            "SearchIndex": search_index,
            "ItemCount": item_count,
            "Resources": [
                "ItemInfo.Title",
                "ItemInfo.ByLineInfo",
                "ItemInfo.Features",
                "ItemInfo.TechnicalInfo",
                "Offers.Listings.Price",
                "Offers.Listings.IsPrimeEligible",
                "Images.Primary.Large",
                "CustomerReviews.Count",
                "CustomerReviews.StarRating",
                "BrowseNodeInfo.BrowseNodes",
            ],
        }

        if min_price:
            payload["MinPrice"] = min_price * 100  # PA-API uses paise
        if max_price:
            payload["MaxPrice"] = max_price * 100

        try:
            headers = self._sign_request(payload)
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    self.ENDPOINT,
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:
                logger.error("PA-API error", status=response.status_code, body=response.text[:200])
                return []

            data = response.json()
            return self._parse_results(data)

        except Exception as e:
            logger.error("PA-API search failed", error=str(e))
            return []

    def _parse_results(self, data: dict) -> list[AmazonProduct]:
        """Parse PA-API response into AmazonProduct objects."""
        products = []

        items = data.get("SearchResult", {}).get("Items", [])
        for item in items:
            try:
                asin = item.get("ASIN", "")
                if not asin:
                    continue

                # Title
                name = (
                    item.get("ItemInfo", {})
                    .get("Title", {})
                    .get("DisplayValue", "")
                )

                # Brand
                brand = (
                    item.get("ItemInfo", {})
                    .get("ByLineInfo", {})
                    .get("Brand", {})
                    .get("DisplayValue", "")
                )

                # Price
                price = 0.0
                listings = item.get("Offers", {}).get("Listings", [])
                is_prime = False
                if listings:
                    price_data = listings[0].get("Price", {})
                    price = float(price_data.get("Amount", 0))
                    is_prime = listings[0].get("IsPrimeEligible", False)

                # Rating & reviews
                reviews = item.get("CustomerReviews", {})
                rating = float(reviews.get("StarRating", {}).get("Value", 0))
                review_count = int(reviews.get("Count", {}).get("Value", 0))

                # Image
                image_url = (
                    item.get("Images", {})
                    .get("Primary", {})
                    .get("Large", {})
                    .get("URL")
                )

                # URLs
                amazon_url = f"https://www.amazon.in/dp/{asin}"
                affiliate_url = f"{amazon_url}?tag={self.partner_tag}"

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
                    category="Electronics",
                    is_prime=is_prime,
                ))

            except Exception as e:
                logger.warning("Failed to parse product", error=str(e))
                continue

        return products

    def _sign_request(self, payload: dict) -> dict:
        """Sign request with AWS Signature Version 4."""
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        payload_json = json.dumps(payload, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.HOST}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems\n"
        )
        signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"

        canonical_request = "\n".join([
            "POST",
            "/paapi5/searchitems",
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        credential_scope = f"{date_stamp}/{self.REGION}/{self.SERVICE}/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ])

        def sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        signing_key = sign(
            sign(
                sign(
                    sign(f"AWS4{self.secret_key}".encode(), date_stamp),
                    self.REGION,
                ),
                self.SERVICE,
            ),
            "aws4_request",
        )

        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

        authorization = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "content-encoding": "amz-1.0",
            "content-type": "application/json; charset=utf-8",
            "host": self.HOST,
            "x-amz-date": amz_date,
            "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
            "Authorization": authorization,
        }


class AmazonSearchFallback:
    """
    Fallback when PA-API credentials are not configured.
    Uses real Amazon search URLs — always works, affiliate tag tracked.
    """

    def __init__(self, affiliate_tag: str = "whatsay-21"):
        self.affiliate_tag = affiliate_tag

    def build_search_url(self, query: str) -> str:
        """Build Amazon India search URL with affiliate tag."""
        return f"https://www.amazon.in/s?k={quote_plus(query)}&tag={self.affiliate_tag}"

    def build_product_url(self, asin: str) -> str:
        """Build direct product URL with affiliate tag."""
        return f"https://www.amazon.in/dp/{asin}?tag={self.affiliate_tag}"
