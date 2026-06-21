from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from app.core.config import settings
import re


class AffiliateService:
    """Service for managing Amazon affiliate links."""

    def build_affiliate_url(
        self,
        product_url: str,
        tag: str | None = None,
    ) -> str:
        """Add affiliate tag to Amazon URL."""
        affiliate_tag = tag or settings.AMAZON_AFFILIATE_TAG

        try:
            parsed = urlparse(product_url)
            # Parse existing query params
            params = parse_qs(parsed.query, keep_blank_values=True)
            params["tag"] = [affiliate_tag]

            # Rebuild query string
            new_query = urlencode(
                {k: v[0] for k, v in params.items()}, doseq=False
            )

            new_url = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment,
                )
            )
            return new_url
        except Exception:
            return product_url

    def extract_asin(self, url: str) -> str | None:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/product/([A-Z0-9]{10})",
            r"asin=([A-Z0-9]{10})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def build_amazon_url(self, asin: str, marketplace: str = "in") -> str:
        """Build Amazon URL from ASIN."""
        base_urls = {
            "in": "https://www.amazon.in",
            "com": "https://www.amazon.com",
            "co.uk": "https://www.amazon.co.uk",
        }
        base = base_urls.get(marketplace, "https://www.amazon.in")
        return f"{base}/dp/{asin}"

    def is_valid_amazon_url(self, url: str) -> bool:
        """Check if URL is a valid Amazon URL."""
        try:
            parsed = urlparse(url)
            return "amazon" in parsed.netloc
        except Exception:
            return False
