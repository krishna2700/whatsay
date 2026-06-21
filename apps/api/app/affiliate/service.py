from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, quote_plus
from app.core.config import settings
import re


class AffiliateService:
    """Service for managing Amazon affiliate links."""

    def build_affiliate_url(
        self,
        product_url: str,
        tag: str | None = None,
    ) -> str:
        """Add affiliate tag to any Amazon URL (search or product page)."""
        affiliate_tag = tag or settings.AMAZON_AFFILIATE_TAG

        try:
            parsed = urlparse(product_url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            params["tag"] = [affiliate_tag]

            new_query = urlencode(
                {k: v[0] for k, v in params.items()}, doseq=False
            )

            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))
        except Exception:
            return product_url

    def build_search_affiliate_url(
        self,
        search_query: str,
        tag: str | None = None,
    ) -> str:
        """
        Build Amazon India search URL with affiliate tag.
        Always works — no 404 possible.
        Format: https://www.amazon.in/s?k=QUERY&tag=whatsay-21
        """
        affiliate_tag = tag or settings.AMAZON_AFFILIATE_TAG
        encoded = quote_plus(search_query)
        return f"https://www.amazon.in/s?k={encoded}&tag={affiliate_tag}"

    def extract_asin(self, url: str) -> str | None:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"asin=([A-Z0-9]{10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def is_valid_amazon_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return "amazon" in parsed.netloc
        except Exception:
            return False
