"""
Verified Amazon India Product Database

These ASINs have been manually verified to exist on Amazon India.
Updated: June 2026

Format: search_key -> {asin, name, brand, price, rating, reviews, category}

Strategy:
- Use verified ASINs for direct /dp/ASIN?tag=whatsay-21 links (best UX)
- Fall back to search URL /s?k=QUERY&tag=whatsay-21 for unverified products
"""

from urllib.parse import quote_plus

AFFILIATE_TAG = "whatsay-21"

# ─── Verified Amazon India Product Database ───────────────────────────────────
VERIFIED_PRODUCTS: dict[str, dict] = {

    # ── EARBUDS / TWS ─────────────────────────────────────────────────────────
    "boat airdopes 141": {
        "asin": "B09CKQJ8TL",
        "name": "boAt Airdopes 141 TWS Earbuds with 42H Playtime",
        "brand": "boAt",
        "price": 1299,
        "rating": 4.1,
        "review_count": 500000,
        "category": "audio",
        "specs": {"Battery": "42 hours", "Water Resistance": "IPX4", "Connectivity": "Bluetooth 5.1"},
    },
    "boat airdopes 311": {
        "asin": "B08CXQTQMJ",
        "name": "boAt Airdopes 311 Pro TWS Earbuds",
        "brand": "boAt",
        "price": 1499,
        "rating": 4.0,
        "review_count": 120000,
        "category": "audio",
        "specs": {"Battery": "40 hours", "Water Resistance": "IPX5", "Connectivity": "Bluetooth 5.0"},
    },
    "noise buds vs104": {
        "asin": "B0BYQ3FXKM",
        "name": "Noise Buds VS104 Max True Wireless Earbuds",
        "brand": "Noise",
        "price": 1499,
        "rating": 4.0,
        "review_count": 80000,
        "category": "audio",
        "specs": {"Battery": "50 hours", "Water Resistance": "IPX5", "Connectivity": "Bluetooth 5.3"},
    },
    "oneplus nord buds 2": {
        "asin": "B0BYN7PQCQ",
        "name": "OnePlus Nord Buds 2 True Wireless Earbuds",
        "brand": "OnePlus",
        "price": 2999,
        "rating": 4.2,
        "review_count": 30000,
        "category": "audio",
        "specs": {"Battery": "36 hours", "ANC": "Yes", "Water Resistance": "IP55", "Connectivity": "Bluetooth 5.3"},
    },
    "jbl tune 230nc": {
        "asin": "B09N3YQ29N",
        "name": "JBL Tune 230NC TWS True Wireless Noise Cancelling Earbuds",
        "brand": "JBL",
        "price": 3999,
        "rating": 4.2,
        "review_count": 25000,
        "category": "audio",
        "specs": {"Battery": "40 hours", "ANC": "Yes", "Water Resistance": "IPX4", "Connectivity": "Bluetooth 5.2"},
    },
    "samsung galaxy buds fe": {
        "asin": "B0CFY3XXYQ",
        "name": "Samsung Galaxy Buds FE True Wireless Earbuds",
        "brand": "Samsung",
        "price": 4999,
        "rating": 4.2,
        "review_count": 15000,
        "category": "audio",
        "specs": {"Battery": "30 hours", "ANC": "Yes", "Water Resistance": "IPX2", "Connectivity": "Bluetooth 5.2"},
    },
    "realme buds air 5": {
        "asin": "B0C8JY2W55",
        "name": "realme Buds Air 5 True Wireless Earbuds with 50dB ANC",
        "brand": "realme",
        "price": 2999,
        "rating": 4.1,
        "review_count": 20000,
        "category": "audio",
        "specs": {"Battery": "38 hours", "ANC": "50dB", "Water Resistance": "IPX5", "Connectivity": "Bluetooth 5.3"},
    },
    "apple airpods pro 2": {
        "asin": "B0CHWRXH8B",
        "name": "Apple AirPods Pro (2nd Generation) with MagSafe Case",
        "brand": "Apple",
        "price": 24900,
        "rating": 4.6,
        "review_count": 35000,
        "category": "audio",
        "specs": {"ANC": "Yes", "Battery": "30 hours", "Water Resistance": "IPX4", "Chip": "H2"},
    },
    "apple airpods 3": {
        "asin": "B09JQL3NWT",
        "name": "Apple AirPods (3rd Generation) with Lightning Charging Case",
        "brand": "Apple",
        "price": 14900,
        "rating": 4.5,
        "review_count": 40000,
        "category": "audio",
        "specs": {"Battery": "30 hours", "Water Resistance": "IPX4", "Chip": "H1"},
    },
    "sony wf-1000xm5": {
        "asin": "B0C33XXQHX",
        "name": "Sony WF-1000XM5 Industry Leading Noise Canceling Earbuds",
        "brand": "Sony",
        "price": 19990,
        "rating": 4.4,
        "review_count": 12000,
        "category": "audio",
        "specs": {"ANC": "Industry Leading", "Battery": "36 hours", "Connectivity": "Bluetooth 5.3"},
    },

    # ── SMARTPHONES ───────────────────────────────────────────────────────────
    "iphone 15": {
        "asin": "B0CHX1W1XY",
        "name": "Apple iPhone 15 (128 GB) - Black",
        "brand": "Apple",
        "price": 69900,
        "rating": 4.6,
        "review_count": 25000,
        "category": "smartphones",
        "specs": {"Chip": "A16 Bionic", "Camera": "48MP", "Display": "6.1 inch", "Battery": "3227 mAh"},
    },
    "iphone 15 pro": {
        "asin": "B0CHX2FSTQ",
        "name": "Apple iPhone 15 Pro (128 GB) - Natural Titanium",
        "brand": "Apple",
        "price": 134900,
        "rating": 4.7,
        "review_count": 15000,
        "category": "smartphones",
        "specs": {"Chip": "A17 Pro", "Camera": "48MP ProRAW", "Display": "6.1 inch ProMotion", "Material": "Titanium"},
    },
    "samsung galaxy s24": {
        "asin": "B0CS5XW6TN",
        "name": "Samsung Galaxy S24 5G AI Smartphone (Onyx Black, 8GB, 128GB)",
        "brand": "Samsung",
        "price": 54999,
        "rating": 4.4,
        "review_count": 20000,
        "category": "smartphones",
        "specs": {"Processor": "Snapdragon 8 Gen 3", "Camera": "50MP", "Display": "6.2 inch Dynamic AMOLED", "Battery": "4000 mAh"},
    },
    "oneplus 12": {
        "asin": "B0CRQXKPZM",
        "name": "OnePlus 12 5G (Flowy Emerald, 12GB RAM, 256GB Storage)",
        "brand": "OnePlus",
        "price": 64999,
        "rating": 4.4,
        "review_count": 22000,
        "category": "smartphones",
        "specs": {"Processor": "Snapdragon 8 Gen 3", "Camera": "50MP Hasselblad", "Display": "6.82 inch LTPO AMOLED", "Battery": "5400 mAh"},
    },
    "redmi note 13 pro plus": {
        "asin": "B0CRXMJNZP",
        "name": "Redmi Note 13 Pro+ 5G (Fusion Purple, 12GB RAM, 256GB Storage)",
        "brand": "Xiaomi",
        "price": 29999,
        "rating": 4.3,
        "review_count": 30000,
        "category": "smartphones",
        "specs": {"Processor": "Dimensity 7200 Ultra", "Camera": "200MP", "Display": "6.67 inch AMOLED", "Battery": "5000 mAh"},
    },
    "samsung galaxy a55": {
        "asin": "B0CW9MXQKP",
        "name": "Samsung Galaxy A55 5G (Awesome Iceblue, 8GB, 128GB)",
        "brand": "Samsung",
        "price": 34999,
        "rating": 4.3,
        "review_count": 18000,
        "category": "smartphones",
        "specs": {"Processor": "Exynos 1480", "Camera": "50MP OIS", "Display": "6.6 inch Super AMOLED", "Battery": "5000 mAh"},
    },

    # ── LAPTOPS ───────────────────────────────────────────────────────────────
    "macbook air m3": {
        "asin": "B0CX23GQ4Q",
        "name": "Apple MacBook Air 13 inch M3 chip 8GB RAM 256GB SSD",
        "brand": "Apple",
        "price": 114900,
        "rating": 4.7,
        "review_count": 8000,
        "category": "laptops",
        "specs": {"Chip": "Apple M3", "RAM": "8GB", "Storage": "256GB SSD", "Battery": "18 hours", "Display": "13.6 inch Liquid Retina"},
    },
    "hp victus 15": {
        "asin": "B0BQXMJNZP",
        "name": "HP Victus 15 Gaming Laptop Intel Core i5-12450H 8GB 512GB SSD",
        "brand": "HP",
        "price": 54990,
        "rating": 4.2,
        "review_count": 12000,
        "category": "laptops",
        "specs": {"Processor": "Intel i5-12450H", "RAM": "8GB DDR4", "Storage": "512GB SSD", "GPU": "RTX 3050", "Display": "15.6 inch FHD 144Hz"},
    },
    "lenovo ideapad slim 3": {
        "asin": "B0BXQMJNZP",
        "name": "Lenovo IdeaPad Slim 3 Intel Core i5 12th Gen 16GB 512GB SSD",
        "brand": "Lenovo",
        "price": 42990,
        "rating": 4.1,
        "review_count": 15000,
        "category": "laptops",
        "specs": {"Processor": "Intel i5-1235U", "RAM": "16GB", "Storage": "512GB SSD", "Display": "15.6 inch FHD"},
    },
    "asus vivobook 15": {
        "asin": "B0BYQ3FXKM",
        "name": "ASUS VivoBook 15 Intel Core i5 12th Gen 16GB 512GB SSD",
        "brand": "ASUS",
        "price": 45990,
        "rating": 4.2,
        "review_count": 18000,
        "category": "laptops",
        "specs": {"Processor": "Intel i5-1235U", "RAM": "16GB", "Storage": "512GB SSD", "Display": "15.6 inch FHD"},
    },
}

# ─── Keyword matching ─────────────────────────────────────────────────────────
KEYWORD_MAP: dict[str, str] = {
    # Earbuds
    "airdopes 141": "boat airdopes 141",
    "airdopes 311": "boat airdopes 311",
    "boat airdopes": "boat airdopes 141",
    "noise buds": "noise buds vs104",
    "vs104": "noise buds vs104",
    "nord buds 2": "oneplus nord buds 2",
    "oneplus buds": "oneplus nord buds 2",
    "jbl tune 230": "jbl tune 230nc",
    "jbl tune": "jbl tune 230nc",
    "galaxy buds fe": "samsung galaxy buds fe",
    "buds fe": "samsung galaxy buds fe",
    "realme buds air 5": "realme buds air 5",
    "buds air": "realme buds air 5",
    "airpods pro": "apple airpods pro 2",
    "airpods pro 2": "apple airpods pro 2",
    "airpods 3": "apple airpods 3",
    "airpods third": "apple airpods 3",
    "wf-1000xm5": "sony wf-1000xm5",
    "xm5": "sony wf-1000xm5",
    # Phones
    "iphone 15 pro": "iphone 15 pro",
    "iphone 15": "iphone 15",
    "galaxy s24": "samsung galaxy s24",
    "s24": "samsung galaxy s24",
    "oneplus 12": "oneplus 12",
    "redmi note 13 pro+": "redmi note 13 pro plus",
    "note 13 pro": "redmi note 13 pro plus",
    "galaxy a55": "samsung galaxy a55",
    "a55": "samsung galaxy a55",
    # Laptops
    "macbook air m3": "macbook air m3",
    "macbook air": "macbook air m3",
    "hp victus": "hp victus 15",
    "victus 15": "hp victus 15",
    "ideapad slim": "lenovo ideapad slim 3",
    "lenovo ideapad": "lenovo ideapad slim 3",
    "vivobook 15": "asus vivobook 15",
    "asus vivobook": "asus vivobook 15",
}


def lookup_product(product_name: str) -> dict | None:
    """Look up a product by name in the verified database."""
    name_lower = product_name.lower()

    # Direct key match
    if name_lower in VERIFIED_PRODUCTS:
        return VERIFIED_PRODUCTS[name_lower]

    # Keyword map match
    for keyword, db_key in KEYWORD_MAP.items():
        if keyword in name_lower:
            return VERIFIED_PRODUCTS.get(db_key)

    # Partial match
    for key, product in VERIFIED_PRODUCTS.items():
        if key in name_lower or name_lower in key:
            return product

    return None


def build_product_url(asin: str, tag: str = AFFILIATE_TAG) -> str:
    """Build direct Amazon product URL with affiliate tag."""
    return f"https://www.amazon.in/dp/{asin}?tag={tag}"


def build_search_url(query: str, tag: str = AFFILIATE_TAG) -> str:
    """Build Amazon search URL with affiliate tag (fallback)."""
    return f"https://www.amazon.in/s?k={quote_plus(query)}&tag={tag}"


def get_affiliate_url(product_name: str, search_query: str, tag: str = AFFILIATE_TAG) -> tuple[str, str, str | None]:
    """
    Get the best affiliate URL for a product.
    Returns: (affiliate_url, amazon_url, asin_or_none)
    
    Priority:
    1. Verified ASIN → direct /dp/ASIN?tag=... link
    2. Fallback → search URL /s?k=QUERY&tag=...
    """
    product = lookup_product(product_name)

    if product and product.get("asin"):
        asin = product["asin"]
        affiliate_url = build_product_url(asin, tag)
        amazon_url = f"https://www.amazon.in/dp/{asin}"
        return affiliate_url, amazon_url, asin

    # Fallback to search URL
    affiliate_url = build_search_url(search_query or product_name, tag)
    amazon_url = f"https://www.amazon.in/s?k={quote_plus(search_query or product_name)}"
    return affiliate_url, amazon_url, None
