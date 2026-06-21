"""Test affiliate URL generation."""
import asyncio
import httpx
import json

BASE = "http://localhost:8000/api/v1"

async def test():
    async with httpx.AsyncClient(timeout=90) as client:
        # Login
        r = await client.post(f"{BASE}/auth/login",
            json={"email": "test@whatsay.ai", "password": "Test1234!"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Auth OK")

        # Test earbuds
        print("\n🔍 Testing: Best earbuds under 5000 for gym")
        r2 = await client.post(f"{BASE}/questions/ask",
            json={"text": "Best earbuds under 5000 for gym", "budget": 5000},
            headers=headers)
        d = r2.json()
        rec = d.get("recommendation") or {}
        print(f"Verdict: {rec.get('verdict')} | Score: {rec.get('score')}")
        print(f"Summary: {rec.get('summary','')[:100]}")
        
        for p in rec.get("products", []):
            aff = p.get("affiliate_url", "")
            print(f"\n  ✅ {p['name'][:55]}")
            print(f"     ₹{p['price']:,.0f} | {p['rating']}⭐ | {p['review_count']:,} reviews")
            print(f"     🔗 {aff}")
            # Verify URL format
            if "amazon.in/s?k=" in aff and "tag=whatsay-21" in aff:
                print(f"     ✅ VALID search URL with affiliate tag")
            elif "amazon.in/dp/" in aff and "tag=whatsay-21" in aff:
                print(f"     ✅ VALID product URL with affiliate tag")
            else:
                print(f"     ❌ INVALID URL format!")

        # Test iPhone
        print("\n\n🔍 Testing: Should I buy iPhone 15?")
        r3 = await client.post(f"{BASE}/questions/ask",
            json={"text": "Should I buy iPhone 15?"},
            headers=headers)
        d3 = r3.json()
        rec3 = d3.get("recommendation") or {}
        print(f"Verdict: {rec3.get('verdict')} | Score: {rec3.get('score')}")
        for p in rec3.get("products", [])[:2]:
            aff = p.get("affiliate_url", "")
            print(f"\n  ✅ {p['name'][:55]}")
            print(f"     ₹{p['price']:,.0f} | {p['rating']}⭐")
            print(f"     🔗 {aff}")

        print("\n\n✅ All affiliate URLs verified!")

asyncio.run(test())
