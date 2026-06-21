import asyncio, httpx, json

BASE = "http://localhost:8000/api/v1"

async def test():
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(f"{BASE}/auth/login", json={"email":"test@whatsay.ai","password":"Test1234!"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Auth OK\n")

        tests = [
            ("Best earbuds under 5000 for gym", 5000),
            ("Should I buy iPhone 15?", None),
            ("Best laptop under 80000 for programming", 80000),
            ("Should I buy Tata Nexon?", None),
        ]

        for question, budget in tests:
            print(f"{'='*60}")
            print(f"Q: {question}")
            payload = {"text": question}
            if budget:
                payload["budget"] = budget
            r2 = await c.post(f"{BASE}/questions/ask", json=payload, headers=headers)
            d = r2.json()
            rec = d.get("recommendation") or {}
            print(f"Verdict: {rec.get('verdict')} | Score: {rec.get('score')}")
            prods = rec.get("products", [])
            print(f"Products: {len(prods)}")
            for p in prods[:3]:
                aff = p.get("affiliate_url","")
                asin = p.get("asin","")
                url_type = "DIRECT ✅" if "/dp/" in aff else "SEARCH 🔍"
                print(f"  {url_type} {p['name'][:45]}")
                print(f"    ₹{p['price']:,.0f} | {p['rating']}⭐ | ASIN:{asin or 'N/A'}")
                print(f"    {aff[:75]}")
            print()

asyncio.run(test())
