# Freelancer.com API Guide

**Project:** FreelanceMCP  
**App Owner:** Abhishek Rathore  
**App Status:** Pending Approval  
**Last Updated:** 2026-04-01

---

## Table of Contents

1. [App Credentials](#1-app-credentials)
2. [Environment Setup](#2-environment-setup)
3. [All CLI Commands](#3-all-cli-commands)
4. [Python Script Examples](#4-python-script-examples)
5. [API Endpoints Reference](#5-api-endpoints-reference)
6. [Response Format](#6-response-format)
7. [Search Filters & Parameters](#7-search-filters--parameters)
8. [Error Handling](#8-error-handling)
9. [Rate Limits & Caching](#9-rate-limits--caching)
10. [Pending Approval Notes](#10-pending-approval-notes)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. App Credentials

| Field                  | Value                                      |
| ---------------------- | ------------------------------------------ |
| **App ID (Client ID)** | `a33962b5-a7f0-486a-812b-00f079dd6c1b`     |
| **Secret**             | `9f1793aa3d...0ef2` (stored in `.env.dev`) |
| **Access Token**       | `6pz7cldX3QgDj6K67xf1RGwEIbZvNs`           |
| **Homepage**           | `http://localhost:8080/callback`           |
| **Redirect URI**       | `http://localhost:8080/callback`           |
| **Scopes**             | `basic`, `fln:project_manage`              |
| **User Limit**         | 5                                          |
| **Status**             | ⏳ Pending Approval                        |

> **Security Note:** Never commit `.env.dev` to version control. These credentials should remain local only.

---

## 2. Environment Setup

### `.env.dev` Configuration

```env
FREELANCER_CLIENT_ID=a33962b5-a7f0-486a-812b-00f079dd6c1b
FREELANCER_CLIENT_SECRET=9f1793aa3d724201175429b923bfaa7a8f63e9ebadcc4cd5983a9b90ff8942eb30a57af17ba95cf8816b1dec5fa20b321129f417cddd13a12b8b40dc7f7c0ef2
FREELANCER_OAUTH_TOKEN=6pz7cldX3QgDj6K67xf1RGwEIbZvNs
ENABLED_PLATFORMS=freelancer
```

All commands below use `APP_ENV=dev` to auto-load these values.

---

## 3. All CLI Commands

### Basic Search

```bash
# Search with default skills (Python, Django, React)
APP_ENV=dev python freelance_api_clients.py
```

**Expected Output (after approval):**

```
✅ Freelancer: API client initialized
✅ Freelancer.com: Found 10 gigs

Total gigs found: 10
Platforms searched: ['freelancer']

Top 3 matches:
1. Build Django REST API for Mobile App
   Platform: freelancer
   Budget: USD 500-1500
   Match: 85.0%
   URL: https://www.freelancer.com/projects/python-django/build-django-rest-api

2. Python Web Scraper for E-commerce
   Platform: freelancer
   Budget: USD 200-400
   Match: 70.0%
   URL: https://www.freelancer.com/projects/python/web-scraper-ecommerce

3. React + Django Full Stack App
   Platform: freelancer
   Budget: USD 1000-3000
   Match: 60.0%
   URL: https://www.freelancer.com/projects/react/fullstack-app
```

---

### Search with Custom Skills

```bash
APP_ENV=dev python << 'EOF'
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import search_freelance_gigs

async def main():
    results = await search_freelance_gigs(
        skills=['Python', 'Django'],
        platforms=['freelancer'],
        limit=10
    )
    print(f"Total: {results['total_found']}")
    for gig in results['gigs']:
        print(f"- {gig['title']} | {gig['budget']} | Match: {gig['match_score']*100:.0f}%")

asyncio.run(main())
EOF
```

---

### Search with Budget Filter

```bash
APP_ENV=dev python << 'EOF'
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import search_freelance_gigs

async def main():
    results = await search_freelance_gigs(
        skills=['React', 'TypeScript'],
        min_budget=500,
        max_budget=3000,
        platforms=['freelancer'],
        limit=5
    )
    for gig in results['gigs']:
        print(f"Title: {gig['title']}")
        print(f"  Budget: {gig['budget']}")
        print(f"  Skills: {gig['skills_required']}")
        print(f"  Proposals: {gig['proposals_count']}")
        print(f"  URL: {gig['url']}")
        print()

asyncio.run(main())
EOF
```

---

### Search Fixed Price Only

```bash
APP_ENV=dev python << 'EOF'
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import search_freelance_gigs

async def main():
    results = await search_freelance_gigs(
        skills=['Node.js', 'MongoDB'],
        project_type='fixed_price',
        max_budget=2000,
        platforms=['freelancer'],
        limit=10
    )
    print(f"Fixed price gigs found: {results['total_found']}")
    for gig in results['gigs']:
        print(f"- [{gig['project_type']}] {gig['title']} — {gig['budget']}")

asyncio.run(main())
EOF
```

---

### Search Hourly Projects

```bash
APP_ENV=dev python << 'EOF'
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import search_freelance_gigs

async def main():
    results = await search_freelance_gigs(
        skills=['Python', 'Machine Learning'],
        project_type='hourly',
        platforms=['freelancer'],
        limit=10
    )
    for gig in results['gigs']:
        print(f"Title: {gig['title']}")
        print(f"  Rate: {gig['budget']}")
        print(f"  Client Rating: {gig['client_rating']}")
        print()

asyncio.run(main())
EOF
```

---

### Search with High Match Score Filter

```bash
APP_ENV=dev python << 'EOF'
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import FreelancerAPIClient, SearchCriteria

async def main():
    client = FreelancerAPIClient()
    criteria = SearchCriteria(
        skills=['Python', 'Django', 'REST API'],
        max_budget=5000,
        min_match_score=0.7,   # Only gigs with 70%+ skill match
        limit=20
    )
    gigs = await client.search_gigs(criteria)
    print(f"High-match gigs: {len(gigs)}")
    for gig in gigs:
        print(f"- {gig.title} | Match: {gig.match_score*100:.0f}% | {gig.budget}")

asyncio.run(main())
EOF
```

---

### Raw API Call (Direct HTTP)

```bash
APP_ENV=dev python << 'EOF'
import asyncio, os, json
from dotenv import load_dotenv
load_dotenv('.env.dev')
import aiohttp

async def main():
    token = os.getenv('FREELANCER_OAUTH_TOKEN')
    url = 'https://www.freelancer.com/api/projects/0.1/projects/active'
    params = {
        'query': 'Python Django',
        'limit': 5,
        'job_details': 'true',
        'user_details': 'true'
    }
    headers = {'Freelancer-OAuth-V1': token}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            print(f"HTTP Status: {resp.status}")
            data = await resp.json()
            print(json.dumps(data, indent=2)[:3000])

asyncio.run(main())
EOF
```

---

### Verify Token is Loaded

```bash
APP_ENV=dev python << 'EOF'
from dotenv import load_dotenv
import os
load_dotenv('.env.dev')
print('FREELANCER_OAUTH_TOKEN:', os.getenv('FREELANCER_OAUTH_TOKEN'))
print('FREELANCER_CLIENT_ID:', os.getenv('FREELANCER_CLIENT_ID'))
EOF
```

**Expected Output:**

```
FREELANCER_OAUTH_TOKEN: 6pz7cldX3QgDj6K67xf1RGwEIbZvNs
FREELANCER_CLIENT_ID: a33962b5-a7f0-486a-812b-00f079dd6c1b
```

---

### Test Connection & Auth

```bash
APP_ENV=dev python << 'EOF'
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import FreelancerAPIClient

client = FreelancerAPIClient()
authenticated = client.authenticate()
print('Authenticated:', authenticated)
EOF
```

**Expected Output:**

```
Authenticated: True
```

---

### Run via MCP Server Tool

```bash
# Start the server, then call search_gigs tool with use_real_api=True
APP_ENV=dev python freelance_server.py stdio
```

From Claude Desktop or MCP client:

```
"Search for Python gigs under $3000 on Freelancer"
```

---

## 4. Python Script Examples

### Full Search Script

```python
#!/usr/bin/env python3
"""Freelancer.com search script"""

import asyncio
import os
from dotenv import load_dotenv

# Load dev environment
load_dotenv('.env.dev')

from freelance_api_clients import search_freelance_gigs


async def search(skills, max_budget=None, min_budget=None, project_type=None, limit=10):
    results = await search_freelance_gigs(
        skills=skills,
        max_budget=max_budget,
        min_budget=min_budget,
        project_type=project_type,
        platforms=['freelancer'],
        limit=limit
    )

    print(f"\n{'='*60}")
    print(f"Search: {skills}")
    print(f"Total Found: {results['total_found']}")
    print(f"Platforms: {results['platforms_searched']}")
    print(f"{'='*60}\n")

    for i, gig in enumerate(results['gigs'], 1):
        print(f"{i}. {gig['title']}")
        print(f"   Budget: {gig['budget']}")
        print(f"   Skills: {', '.join(gig['skills_required'])}")
        print(f"   Match: {gig['match_score']*100:.0f}%")
        print(f"   Proposals: {gig['proposals_count']}")
        print(f"   Posted: {gig['posted_date']}")
        print(f"   URL: {gig['url']}")
        print()

    return results


if __name__ == "__main__":
    asyncio.run(search(
        skills=["Python", "Django", "React"],
        max_budget=5000,
        limit=10
    ))
```

Run it:

```bash
APP_ENV=dev python your_script.py
```

---

### Direct FreelancerAPIClient Usage

```python
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')

from freelance_api_clients import FreelancerAPIClient, SearchCriteria

async def main():
    client = FreelancerAPIClient()

    criteria = SearchCriteria(
        skills=["Python", "Flask", "PostgreSQL"],
        min_budget=300,
        max_budget=2000,
        project_type="fixed_price",
        min_match_score=0.5,
        limit=15,
        offset=0           # Pagination: increment by 'limit' for next page
    )

    gigs = await client.search_gigs(criteria)

    for gig in gigs:
        print(f"ID: {gig.id}")
        print(f"Title: {gig.title}")
        print(f"Platform: {gig.platform}")
        print(f"Budget: {gig.budget} (min={gig.budget_min}, max={gig.budget_max})")
        print(f"Type: {gig.project_type}")
        print(f"Skills: {gig.skills_required}")
        print(f"Match Score: {gig.match_score:.2f}")
        print(f"Proposals: {gig.proposals_count}")
        print(f"Client Rating: {gig.client_rating}")
        print(f"Client Reviews: {gig.client_reviews}")
        print(f"Posted: {gig.posted_date}")
        print(f"URL: {gig.url}")
        print("-" * 40)

asyncio.run(main())
```

---

## 5. API Endpoints Reference

| Endpoint                            | Method | Purpose                   |
| ----------------------------------- | ------ | ------------------------- |
| `/api/projects/0.1/projects/active` | GET    | Search active projects    |
| `/api/projects/0.1/projects/{id}`   | GET    | Get project details by ID |
| `/api/projects/0.1/bids/`           | GET    | Get bids for a project    |
| `/api/users/0.1/users/`             | GET    | Get user profile          |
| `/api/projects/0.1/milestones/`     | GET    | Get milestones            |

### Authentication Header

All requests require:

```
Freelancer-OAuth-V1: <your_oauth_token>
```

### Base URL

```
https://www.freelancer.com/api
```

---

## 6. Response Format

### Successful Search Response

```json
{
  "total_found": 10,
  "platforms_searched": ["freelancer"],
  "search_criteria": {
    "skills": ["Python", "Django"],
    "max_budget": 3000,
    "min_budget": null,
    "project_type": "fixed_price"
  },
  "gigs": [
    {
      "id": "freelancer_123456789",
      "platform": "freelancer",
      "title": "Build Django REST API for Mobile App",
      "description": "We need an experienced Django developer to build a REST API...",
      "budget": "USD 800-1500",
      "skills_required": ["Python", "Django", "REST API", "PostgreSQL"],
      "match_score": 0.85,
      "proposals_count": 12,
      "client_rating": 4.8,
      "client_reviews": 37,
      "posted_date": "2026-04-01T06:30:00",
      "url": "https://www.freelancer.com/projects/python-django/build-django-rest-api",
      "project_type": "fixed",
      "budget_min": 800,
      "budget_max": 1500,
      "hourly_rate": null,
      "remote_ok": true
    }
  ]
}
```

### No Credentials Response

```json
{
  "total_found": 0,
  "gigs": [],
  "platforms_searched": [],
  "error": "No API clients configured. Please set API credentials in environment variables."
}
```

### Auth Error (HTTP 401)

```
❌ Freelancer.com: AuthenticationError: Freelancer.com authentication failed
```

### Rate Limit Error (HTTP 429)

```
⚠️ Retrying after rate limit... (attempt 1/3)
⚠️ Retrying after rate limit... (attempt 2/3)
❌ Freelancer.com: RateLimitError after 3 attempts
```

---

## 7. Search Filters & Parameters

### `SearchCriteria` Parameters

| Parameter         | Type        | Default      | Description                                   |
| ----------------- | ----------- | ------------ | --------------------------------------------- |
| `skills`          | `List[str]` | **required** | Skills to match (e.g. `["Python", "Django"]`) |
| `max_budget`      | `float`     | `None`       | Maximum project budget                        |
| `min_budget`      | `float`     | `None`       | Minimum project budget                        |
| `project_type`    | `str`       | `None`       | `"fixed_price"` or `"hourly"`                 |
| `min_match_score` | `float`     | `0.0`        | Minimum skill match ratio (0.0–1.0)           |
| `limit`           | `int`       | `10`         | Results per page (max ~50)                    |
| `offset`          | `int`       | `0`          | Pagination offset                             |

### `search_freelance_gigs()` Parameters

| Parameter      | Type        | Default      | Description                             |
| -------------- | ----------- | ------------ | --------------------------------------- |
| `skills`       | `List[str]` | **required** | Skills list                             |
| `max_budget`   | `float`     | `None`       | Max budget                              |
| `min_budget`   | `float`     | `None`       | Min budget                              |
| `project_type` | `str`       | `None`       | Project type filter                     |
| `platforms`    | `List[str]` | `None` (all) | `["freelancer"]`, `["upwork"]`, or both |
| `limit`        | `int`       | `10`         | Number of results                       |

### Pagination Example

```python
# Page 1
results_p1 = await search_freelance_gigs(skills=["Python"], limit=10)   # offset=0

# Page 2 (use FreelancerAPIClient directly)
criteria = SearchCriteria(skills=["Python"], limit=10, offset=10)
gigs_p2 = await client.search_gigs(criteria)
```

---

## 8. Error Handling

### Error Types

| Error                 | HTTP Status | Cause                 | Auto-Retry            |
| --------------------- | ----------- | --------------------- | --------------------- |
| `AuthenticationError` | 401         | Invalid/expired token | No                    |
| `RateLimitError`      | 429         | Too many requests     | Yes (3x with backoff) |
| `APIError`            | 4xx/5xx     | API-side issue        | No                    |
| `aiohttp.ClientError` | —           | Network issue         | No                    |

### Retry Logic

The client uses **exponential backoff** on rate limit errors:

```
Attempt 1: wait 2s
Attempt 2: wait 4s
Attempt 3: wait 8s
(max 3 attempts then gives up)
```

### Fallback Behavior

If authentication fails or API is unreachable, the server falls back to mock data automatically. Check the `data_source` field in the server tool response:

```json
{
  "data_source": "real_api", // or "mock_data"
  "note": "Live data from Freelancer.com"
}
```

---

## 9. Rate Limits & Caching

### Rate Limiting

- **Default delay:** 1 second between requests
- **Freelancer.com limit:** Not publicly documented (SDK handles automatically)
- Configured via: `RATE_LIMIT_REQUESTS_PER_MINUTE=60` in `.env.dev`

### Caching (TTL Cache)

- Results are cached for **5 minutes** (300 seconds) by default
- Configured via: `CACHE_TTL_SECONDS=300` in `.env.dev`
- Cache is **per-process in-memory** (cleared on restart)
- Cache key includes: `skills + min_budget + max_budget + project_type`

To disable caching (fresh results every call):

```python
client = FreelancerAPIClient(cache_ttl=0)
```

---

## 10. Pending Approval Notes

Your app is currently in **Pending Approval** status. Here's what this means:

| Scope                | Status     | Impact                            |
| -------------------- | ---------- | --------------------------------- |
| `basic`              | ✅ Active  | Can read your own profile         |
| `fln:project_manage` | ⏳ Pending | Cannot search/bid on projects yet |

### What works NOW (before approval):

- Token validation (HTTP 200 on basic endpoints)
- Reading your own user profile (`/api/users/0.1/self/`)

### What requires approval:

- Searching projects (`/api/projects/0.1/projects/active`)
- Reading bids, milestones, proposals

### While Pending — The server falls back gracefully:

```
⚠️ Freelancer.com: Skipping search (authentication scope not approved)
⚠️ No API clients available. Using fallback data.
```

### After Approval:

No code changes needed. Just run the same commands — the token will have elevated access automatically.

---

## 11. Troubleshooting

### "No OAuth token configured"

**Cause:** `.env.dev` not loaded  
**Fix:**

```bash
# Always prefix with APP_ENV=dev
APP_ENV=dev python freelance_api_clients.py

# Or explicitly load in script
load_dotenv('.env.dev')
```

---

### "Authentication failed" (401)

**Cause:** Token expired or scope not approved  
**Fix:**

1. Go to [Freelancer Developer Dashboard](https://www.freelancer.com/developers/registration)
2. Regenerate the Access Token
3. Update `FREELANCER_OAUTH_TOKEN` in `.env.dev`

---

### "Rate limit exceeded" (429)

**Cause:** Too many requests per minute  
**Fix:** Increase delay in client:

```python
client = FreelancerAPIClient()
client.rate_limit_delay = 2.0  # 2 seconds between requests
```

---

### "Total gigs found: 0"

**Causes & Fixes:**

| Cause                | Fix                                    |
| -------------------- | -------------------------------------- |
| App pending approval | Wait for Freelancer to approve         |
| No matching projects | Broaden skills or remove budget filter |
| Token not loaded     | Use `APP_ENV=dev` prefix               |
| Network error        | Check internet connection              |

---

### Check what env vars are loaded

```bash
APP_ENV=dev python << 'EOF'
from dotenv import load_dotenv
import os
load_dotenv('.env.dev')
keys = ['FREELANCER_OAUTH_TOKEN','FREELANCER_CLIENT_ID','FREELANCER_CLIENT_SECRET','ENABLED_PLATFORMS']
for k in keys:
    v = os.getenv(k, 'NOT SET')
    masked = v[:8] + '...' if len(v) > 10 else v
    print(f"{k}: {masked}")
EOF
```

---

## Quick Reference Card

```bash
# ── Environment ──────────────────────────────────────────
APP_ENV=dev python freelance_api_clients.py          # Default test run
APP_ENV=dev python freelance_client.py --check-env   # Env verification

# ── Search Commands ───────────────────────────────────────
# Default search (Python, Django, React)
APP_ENV=dev python freelance_api_clients.py

# Custom skills
APP_ENV=dev python << 'EOF'
import asyncio
from dotenv import load_dotenv
load_dotenv('.env.dev')
from freelance_api_clients import search_freelance_gigs
asyncio.run(search_freelance_gigs(['Python','Flask'], platforms=['freelancer'], limit=10))
EOF

# ── MCP Server ────────────────────────────────────────────
APP_ENV=dev python freelance_server.py stdio         # Start MCP server

# ── Debugging ─────────────────────────────────────────────
APP_ENV=dev python << 'EOF'
from dotenv import load_dotenv; import os
load_dotenv('.env.dev'); print(os.getenv('FREELANCER_OAUTH_TOKEN'))
EOF
```
