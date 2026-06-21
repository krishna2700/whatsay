import asyncio, httpx, json

BASE = "http://localhost:8000/api/v1"

async def test():
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{BASE}/auth/login", json={"email":"test@whatsay.ai","password":"Test1234!"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Auth OK\n")

        tests = [
            ("Best earbuds under 5000 for gym", 5000),
            ("Should I buy iPhone 15?", None),
            ("Should I buy Tata Nexon?", None),
        ]

        for question, budget in tests:
            print(f"{'='*65}")
            print(f"Q: {question}")
            payload = {"text": question}
            if budget: payload["budget"] = budget
            r2 = await c.post(f"{BASE}/questions/ask", json=payload, headers=headers)
            d = r2.json()
            rec = d.get("recommendation") or {}
            print(f"Verdict: {rec.get('verdict')} | Score: {rec.get('score')}")
            print(f"Summary: {rec.get('summary','')[:120]}")
            prods = rec.get("products", [])
            print(f"Products: {len(prods)}")
            for p in prods[:3]:
                aff = p.get("affiliate_url","")
                url_type = "DIRECT /dp/" if "/dp/" in aff else "SEARCH /s?k="
                print(f"  [{url_type}] {p['name'][:50]}")
                print(f"    ₹{p['price']:,.0f} | {p['rating']}⭐ | {p['review_count']:,} reviews")
                print(f"    {aff[:70]}")
            print()

asyncio.run(test())
