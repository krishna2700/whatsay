# WhatSay — AI Powered Buying Advisor & Affiliate Commerce Platform

> **"The AI people ask before spending money."**

[![CI/CD](https://github.com/whatsayai/whatsay/actions/workflows/ci.yml/badge.svg)](https://github.com/whatsayai/whatsay/actions)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12-green)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

---

## 🌟 Overview

WhatSay is a production-ready, AI-native buying advisor platform that helps users make smarter purchasing decisions. Users ask product questions in natural language and receive instant, unbiased AI recommendations with direct Amazon affiliate links.

**Core Value Proposition:** Ask any product question → Get AI analysis → Buy with confidence

---

## 🏗️ Architecture

```
whatsay/
├── apps/
│   ├── web/                    # Next.js 15 Frontend
│   │   ├── src/
│   │   │   ├── app/            # App Router pages
│   │   │   │   ├── (app)/      # Authenticated routes
│   │   │   │   │   ├── ask/    # AI Ask interface
│   │   │   │   │   ├── dashboard/
│   │   │   │   │   ├── recommendations/
│   │   │   │   │   └── analytics/
│   │   │   │   ├── auth/       # Auth pages
│   │   │   │   └── page.tsx    # Landing page
│   │   │   ├── components/
│   │   │   │   ├── ui/         # Design system components
│   │   │   │   ├── layout/     # Navbar, Footer
│   │   │   │   └── features/   # Feature components
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── services/       # API service layer
│   │   │   ├── stores/         # Zustand state stores
│   │   │   ├── types/          # TypeScript types
│   │   │   └── lib/            # Utilities
│   │   └── Dockerfile
│   │
│   └── api/                    # FastAPI Backend
│       ├── app/
│       │   ├── api/v1/         # API endpoints
│       │   │   └── endpoints/
│       │   │       ├── auth.py
│       │   │       ├── questions.py
│       │   │       ├── affiliate.py
│       │   │       └── analytics.py
│       │   ├── ai/             # AI engine
│       │   │   ├── base.py     # Abstract provider
│       │   │   ├── providers/  # OpenAI, Claude
│       │   │   ├── recommendation_engine.py
│       │   │   └── provider_factory.py
│       │   ├── models/         # SQLAlchemy models
│       │   ├── schemas/        # Pydantic schemas
│       │   ├── services/       # Business logic
│       │   ├── repositories/   # Data access layer
│       │   ├── affiliate/      # Affiliate service
│       │   ├── core/           # Config, security, deps
│       │   └── db/             # Database session
│       ├── alembic/            # DB migrations
│       ├── requirements.txt
│       └── Dockerfile
│
├── packages/                   # Shared packages (future)
│   ├── ui/
│   ├── types/
│   ├── config/
│   └── shared/
│
├── .github/workflows/          # CI/CD
├── docker-compose.yml
├── turbo.json
└── package.json
```

---

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (optional)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/whatsayai/whatsay.git
cd whatsay

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Access the app
open http://localhost:3000
```

### Option 2: Local Development

#### Frontend Setup

```bash
cd apps/web
npm install
cp .env.example .env.local
# Edit .env.local

npm run dev
# → http://localhost:3000
```

#### Backend Setup

```bash
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp ../../.env.example .env
# Edit .env with your values

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
# → Docs: http://localhost:8000/docs
```

---

## ⚙️ Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET` | JWT signing secret | `your-secret-key` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `AMAZON_AFFILIATE_TAG` | Amazon Associate tag | `whatsay-21` |

### Optional

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key (fallback provider) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `SENTRY_DSN` | Error tracking |
| `POSTHOG_KEY` | Product analytics |

---

## 🧠 AI System

### Provider Abstraction

WhatSay uses a pluggable AI provider system:

```python
# Switch providers via environment variable
DEFAULT_AI_PROVIDER=openai  # or "anthropic"

# Or programmatically
from app.ai.provider_factory import get_ai_provider

provider = get_ai_provider("anthropic")
engine = RecommendationEngine(provider)
result = await engine.generate_recommendation("Best laptop under ₹80,000?")
```

### Recommendation Flow

```
User Question
     ↓
Intent Detection (buy_specific | compare | find_best | budget_search)
     ↓
AI Analysis (GPT-4o-mini / Claude Sonnet)
     ↓
Structured JSON Response
     ↓
Affiliate Link Injection (tag=whatsay-21)
     ↓
Database Persistence
     ↓
Streaming Response to Client
```

### AI Response Schema

```json
{
  "verdict": "highly_recommended",
  "summary": "...",
  "detailed_analysis": "...",
  "pros": ["..."],
  "cons": ["..."],
  "score": 87,
  "confidence": 92,
  "category": "laptops",
  "intent": "budget_search",
  "products": [
    {
      "name": "MacBook Air M4",
      "brand": "Apple",
      "price": 99900,
      "currency": "INR",
      "rating": 4.8,
      "amazon_url": "https://amazon.in/dp/...",
      "affiliate_url": "https://amazon.in/dp/...?tag=whatsay-21",
      "specs": { "Chip": "M4", "RAM": "16GB" },
      "why_recommended": "Best performance per rupee"
    }
  ]
}
```

---

## 🛒 Affiliate System

### Amazon Affiliate Integration

```python
from app.affiliate.service import AffiliateService

service = AffiliateService()

# Add affiliate tag to any Amazon URL
url = service.build_affiliate_url(
    "https://amazon.in/dp/B0XXXXX",
    tag="whatsay-21"
)
# → "https://amazon.in/dp/B0XXXXX?tag=whatsay-21"

# Extract ASIN from URL
asin = service.extract_asin("https://amazon.in/dp/B0CHX3QBCH")
# → "B0CHX3QBCH"
```

### Per-User Affiliate Tags

Users can configure their own Amazon Associate tags:

```
POST /api/v1/affiliate/settings
{ "amazon_tag": "mystore-21" }
```

---

## 📊 Database Schema

### Core Tables

```sql
users
  id, email, name, hashed_password, avatar_url
  is_active, is_verified, google_id, questions_count
  created_at, updated_at

questions
  id, user_id, text, slug, status, category, intent
  budget, currency, view_count, helpful_count
  created_at, updated_at

recommendations
  id, question_id, verdict, summary, detailed_analysis
  pros[], cons[], score, confidence, ai_model, ai_provider
  created_at, updated_at

recommended_products
  id, recommendation_id, product_id, name, brand, category
  price, currency, rating, review_count, image_url
  amazon_url, affiliate_url, asin, specs{}, why_recommended
  rank, is_alternative

affiliate_clicks
  id, user_id, question_id, product_id, affiliate_url
  ip_address, user_agent, referrer, created_at

affiliate_settings
  id, user_id, amazon_tag, is_active

analytics_events
  id, event_type, user_id, session_id, properties{}
```

---

## 🔌 API Reference

### Authentication

```bash
# Register
POST /api/v1/auth/register
{ "email": "user@example.com", "password": "...", "name": "John" }

# Login
POST /api/v1/auth/login
{ "email": "user@example.com", "password": "..." }

# Get current user
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### Questions

```bash
# Ask a question (standard)
POST /api/v1/questions/ask
{ "text": "Best laptop under ₹80,000?", "budget": 80000 }

# Ask with streaming
POST /api/v1/questions/ask/stream
Content-Type: application/json
# Returns Server-Sent Events

# Get user's questions
GET /api/v1/questions?page=1&per_page=20

# Get by slug (SEO-friendly)
GET /api/v1/questions/slug/{slug}
```

### Analytics

```bash
# Get analytics summary
GET /api/v1/analytics/summary
Authorization: Bearer <token>
```

---

## 🎨 Design System

### Color Palette

| Token | Light | Dark |
|-------|-------|------|
| `--color-primary` | `hsl(262 83% 58%)` | `hsl(263 70% 50%)` |
| `--color-background` | `hsl(0 0% 100%)` | `hsl(222 84% 5%)` |
| `--color-foreground` | `hsl(222 84% 5%)` | `hsl(210 40% 98%)` |

### Typography

- **Display**: Plus Jakarta Sans
- **Body**: Inter
- **Mono**: System monospace

### Key Components

- `<AskInput />` — AI question input with suggestions
- `<RecommendationView />` — Full recommendation display
- `<ProductCard />` — Product with affiliate CTA
- `<VerdictBadge />` — Animated verdict indicator
- `<Navbar />` — Responsive navigation with auth state

---

## 🚢 Deployment

### Vercel (Frontend)

```bash
cd apps/web
npx vercel --prod

# Environment variables in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://api.whatsay.ai
# NEXT_PUBLIC_APP_URL=https://whatsay.ai
```

### Railway (Backend)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
cd apps/api
railway up

# Set environment variables in Railway dashboard
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Use strong `JWT_SECRET` (32+ chars)
- [ ] Configure PostgreSQL with SSL
- [ ] Set up Redis with password
- [ ] Configure CORS origins
- [ ] Enable Sentry error tracking
- [ ] Set up PostHog analytics
- [ ] Configure custom domain
- [ ] Enable HTTPS
- [ ] Set up database backups

---

## 🧪 Testing

```bash
# Frontend type check
cd apps/web && npx tsc --noEmit

# Frontend build
cd apps/web && npm run build

# Backend tests
cd apps/api && pytest tests/ -v

# API health check
curl http://localhost:8000/health
```

---

## 📈 Future Roadmap

### Phase 2 — Growth
- [ ] Flipkart affiliate integration
- [ ] Price history tracking
- [ ] Product comparison tables
- [ ] Email notifications
- [ ] Mobile app (React Native)

### Phase 3 — Monetization
- [ ] Pro subscription tier
- [ ] API access for developers
- [ ] White-label solution
- [ ] Multi-language support

### Phase 4 — Scale
- [ ] Multi-tenant organizations
- [ ] Custom AI model fine-tuning
- [ ] Real-time price alerts
- [ ] Community reviews
- [ ] Browser extension

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Affiliate Disclosure

WhatSay participates in the Amazon Associates Program. We earn commissions from qualifying purchases made through our affiliate links. This does not affect our recommendations — we always prioritize your best interest.

---

<div align="center">
  <strong>Built with ❤️ for smart shoppers everywhere</strong>
  <br />
  <a href="https://whatsay.ai">whatsay.ai</a> · 
  <a href="https://twitter.com/whatsayai">Twitter</a> · 
  <a href="https://github.com/whatsayai">GitHub</a>
</div>
