#!/usr/bin/env python3
"""
Interactive Freelancer.com Gig Search

Usage:
    APP_ENV=dev python search_gigs.py
"""

import asyncio
import os
import select
import smtplib
import subprocess
import sys
from typing import Optional
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

# Load env based on APP_ENV
_app_env = os.getenv("APP_ENV")
_env_file = f".env.{_app_env}" if _app_env else ".env"
if Path(_env_file).exists():
    load_dotenv(_env_file, override=True)

from freelance_api_clients import FreelancerAPIClient, SearchCriteria

_LLM_CACHE = {}


# Maps provider name -> (default model, env key for api key)
_PROVIDER_DEFAULTS = {
    "groq":      ("llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "gemini":    ("gemini-3-flash-preview",         "GEMINI_API_KEY"),
    "mistral":   ("mistral-small-latest",     "MISTRAL_API_KEY"),
    "cerebras":  ("llama-3.3-70b",            "CEREBRAS_API_KEY"),
    "ollama":    ("llama3.2",                 ""),          # local, no key needed
    "openai":    ("gpt-5.3-chat-latest",                  "OPENAI_API_KEY"),
}


def get_llm(provider: Optional[str] = None, model: Optional[str] = None):
    """Create and cache the configured LLM client."""
    provider = (provider or os.getenv("AUTO_BID_AI_PROVIDER", "groq")).strip().lower()
    if provider not in _PROVIDER_DEFAULTS:
        provider = "groq"
    temperature = float(os.getenv("AUTO_BID_AI_TEMPERATURE", "0.7"))

    default_model, api_env_key = _PROVIDER_DEFAULTS[provider]
    model = (model or os.getenv("AUTO_BID_AI_MODEL", default_model)).strip()

    cache_key = (provider, model, temperature)
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key], None, provider, model

    try:
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            api_key = os.getenv(api_env_key, "")
            if not api_key:
                return None, f"{api_env_key} not set", provider, model
            llm = ChatOpenAI(api_key=api_key, model=model, temperature=temperature)

        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv(api_env_key, "")
            if not api_key:
                return None, f"{api_env_key} not set (get free key at aistudio.google.com)", provider, model
            llm = ChatGoogleGenerativeAI(google_api_key=api_key, model=model, temperature=temperature)

        elif provider == "mistral":
            from langchain_mistralai import ChatMistralAI
            api_key = os.getenv(api_env_key, "")
            if not api_key:
                return None, f"{api_env_key} not set (get free key at console.mistral.ai)", provider, model
            llm = ChatMistralAI(mistral_api_key=api_key, model=model, temperature=temperature)

        elif provider == "cerebras":
            from langchain_cerebras import ChatCerebras
            api_key = os.getenv(api_env_key, "")
            if not api_key:
                return None, f"{api_env_key} not set (get free key at cloud.cerebras.ai)", provider, model
            llm = ChatCerebras(cerebras_api_key=api_key, model=model, temperature=temperature)

        elif provider == "ollama":
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model=model, temperature=temperature)

        else:  # groq (default)
            from langchain_groq import ChatGroq
            api_key = os.getenv(api_env_key, "")
            if not api_key:
                return None, f"{api_env_key} not set", provider, model
            llm = ChatGroq(groq_api_key=api_key, model_name=model, temperature=temperature)

    except Exception as exc:
        return None, str(exc), provider, model

    _LLM_CACHE[cache_key] = llm
    return llm, None, provider, model


def choose_auto_bid_ai() -> None:
    """Let the user choose which AI provider/model to use for auto-bid proposals."""
    current_provider = os.getenv("AUTO_BID_AI_PROVIDER", "groq").strip().lower() or "groq"
    default_model, _ = _PROVIDER_DEFAULTS.get(current_provider, ("llama-3.3-70b-versatile", ""))
    current_model = os.getenv("AUTO_BID_AI_MODEL", default_model).strip()

    print(f"\n{CYAN}Choose Proposal AI  (✅ free tier  💰 paid):{RESET}")
    print(f"  1) Groq        - llama-3.3-70b-versatile   ✅ free  (groq.com)")
    print(f"  2) Google Gemini - gemini-3-flash-preview         ✅ free  (aistudio.google.com)")
    print(f"  3) Mistral AI  - mistral-small-latest      ✅ free  (console.mistral.ai)")
    print(f"  4) Cerebras    - llama-3.3-70b             ✅ free  (cloud.cerebras.ai)")
    print(f"  5) Ollama      - llama3.2 (local)          ✅ free, no internet needed")
    print(f"  6) OpenAI      - gpt-5.3-chat-latest                   💰 paid  (platform.openai.com)")
    print(f"  7) Keep current ({current_provider}: {current_model})")

    _choices = {
        "1": ("groq",    "llama-3.3-70b-versatile"),
        "2": ("gemini",  "gemini-3-flash-preview"),
        "3": ("mistral", "mistral-small-latest"),
        "4": ("cerebras","llama-3.3-70b"),
        "5": ("ollama",  "llama3.2"),
        "6": ("openai",  "gpt-5.3-chat-latest"),
    }

    choice = input(f"{CYAN}Enter choice (1-7): {RESET}").strip()

    if choice in _choices:
        prov, mdl = _choices[choice]
        os.environ["AUTO_BID_AI_PROVIDER"] = prov
        os.environ["AUTO_BID_AI_MODEL"] = mdl
        # Flush cache so the new provider is picked up immediately
        _LLM_CACHE.clear()
    elif choice in ("7", ""):
        pass
    else:
        print(f"{YELLOW}Invalid choice. Keeping current AI configuration.{RESET}")

    selected_provider = os.getenv("AUTO_BID_AI_PROVIDER", current_provider)
    selected_model = os.getenv("AUTO_BID_AI_MODEL", current_model)
    print(f"{GREEN}Using {selected_provider} / {selected_model} for proposal generation.{RESET}")


# ── ANSI colours ─────────────────────────────────────────────────────────────
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"

DIVIDER     = f"{DIM}{'─' * 64}{RESET}"
DIVIDER_NEW = f"{GREEN}{'━' * 64}{RESET}"


# ── macOS notifications ───────────────────────────────────────────────────────

def notify(title: str, message: str, url: str = "") -> None:
    """Send a macOS system notification."""
    subtitle = url if url else "Freelancer.com"
    script = (
        f'display notification "{message}" '
        f'with title "🚨 New Gig: {title}" '
        f'subtitle "{subtitle}" '
        f'sound name "Glass"'
    )
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass


def play_sound() -> None:
    """Play a short alert sound using macOS afplay."""
    try:
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Glass.aiff"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# ── Mobile / remote notifications ────────────────────────────────────────────

async def notify_telegram(title: str, budget: str, match: int,
                          bids: int, url: str, skills: list) -> None:
    """Send Telegram message to your phone via Bot API."""
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id or token.startswith("your_"):
        return

    text = (
        f"🚨 *New Freelancer Gig!*\n\n"
        f"*{title}*\n"
        f"💰 {budget}\n"
        f"🎯 Match: {match}%\n"
        f"👥 Bids so far: {bids}\n"
        f"🛠 Skills: {', '.join(skills[:5])}\n\n"
        f"🔗 [View & Bid]({url})"
    )
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
               "disable_web_page_preview": False}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload, timeout=aiohttp.ClientTimeout(total=10)
            )
    except Exception:
        pass


async def notify_slack(title: str, budget: str, match: int,
                       bids: int, url: str) -> None:
    """Send Slack webhook message."""
    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook or webhook.startswith("https://hooks.slack.com/services/YOUR"):
        return

    payload = {"text": (
        f":rotating_light: *New Freelancer Gig!*\n"
        f"*<{url}|{title}>*\n"
        f"💰 {budget}  |  🎯 Match: {match}%  |  👥 Bids: {bids}"
    )}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(webhook, json=payload,
                               timeout=aiohttp.ClientTimeout(total=10))
    except Exception:
        pass


def notify_email(title: str, budget: str, match: int,
                 bids: int, url: str, skills: list) -> None:
    """Send email notification (runs in thread to avoid blocking)."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port   = int(os.getenv("SMTP_PORT", "587"))
    user        = os.getenv("EMAIL_USER", "")
    password    = os.getenv("EMAIL_PASSWORD", "")
    from_email  = os.getenv("FROM_EMAIL", user)

    if not user or not password or user.startswith("your_"):
        return

    body = (
        f"New gig found on Freelancer.com!\n\n"
        f"Title:    {title}\n"
        f"Budget:   {budget}\n"
        f"Match:    {match}%\n"
        f"Bids:     {bids}\n"
        f"Skills:   {', '.join(skills)}\n\n"
        f"View & Bid: {url}"
    )
    msg = MIMEText(body)
    msg["Subject"] = f"🚨 New Gig: {title}"
    msg["From"]    = from_email
    msg["To"]      = user
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
    except Exception:
        pass


async def send_all_notifications(gig) -> None:
    """Fire all configured notification channels for a new gig."""
    title  = gig.title or "Untitled"
    budget = gig.budget or "N/A"
    match  = int(gig.match_score * 100)
    bids   = gig.proposals_count or 0
    url    = gig.url or ""
    skills = gig.skills_required or []

    # macOS desktop
    notify(title, f"{budget} | Match: {match}% | Bids: {bids}", url)
    play_sound()

    # Mobile / remote — run concurrently
    import asyncio as _asyncio
    await _asyncio.gather(
        notify_telegram(title, budget, match, bids, url, skills),
        notify_slack(title, budget, match, bids, url),
    )
    # Email is synchronous — run in executor to avoid blocking
    loop = _asyncio.get_event_loop()
    await loop.run_in_executor(
        None, notify_email, title, budget, match, bids, url, skills
    )


def timed_input(label: str, timeout: int = 10) -> str:
    """Non-blocking input that auto-returns '' after `timeout` seconds."""
    sys.stdout.write(f"{CYAN}{label} (auto-skip in {timeout}s): {RESET}")
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().rstrip("\n").strip()
    print(f"{DIM}  ↩ auto-skipped{RESET}")
    return ""


def prompt(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    value = input(f"{CYAN}{label}{hint}: {RESET}").strip()
    return value if value else default


def prompt_float(label: str, default: str = "") -> float | None:
    raw = prompt(label, default)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        print(f"{YELLOW}  ⚠ Invalid number, ignoring.{RESET}")
        return None


def print_gig(index: int | str, gig, new: bool = False) -> None:
    """Print a single gig in a readable card format."""
    title      = gig.title or "Untitled"
    budget     = gig.budget or "N/A"
    ptype      = (gig.project_type or "").upper()
    match_pct  = int(gig.match_score * 100)
    proposals  = gig.proposals_count or 0
    rating     = f"{gig.client_rating:.1f} ⭐" if gig.client_rating else "No rating"
    skills     = ", ".join(gig.skills_required) if gig.skills_required else "N/A"
    desc       = (gig.description or "").strip()
    short_desc = (desc[:200] + "…") if len(desc) > 200 else desc
    url        = gig.url or "N/A"
    badge      = f" {GREEN}★ NEW{RESET}" if new else ""

    print(f"\n{DIVIDER_NEW if new else DIVIDER}")
    print(f"  {BOLD}#{index}  {title}{RESET}{badge}")
    print(f"  {GREEN}Budget:{RESET} {budget}  {DIM}[{ptype}]{RESET}  |  "
          f"{GREEN}Match:{RESET} {match_pct}%  |  "
          f"{GREEN}Bids:{RESET} {proposals}  |  "
          f"{GREEN}Client:{RESET} {rating}")
    print(f"  {GREEN}Skills:{RESET} {skills}")
    if short_desc:
        print(f"  {GREEN}Description:{RESET} {short_desc}")
    print(f"  {BOLD}{CYAN}URL:{RESET} {url}")


def print_header() -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 64}")
    print("  Freelancer.com Interactive Gig Search")
    print(f"{'═' * 64}{RESET}")


_DEFAULT_SKILLS = (
    "Mobile App Development, iPhone, Android, Swift, MySQL, App Developer, Objective C, "
    "iPad, HTML5, Apple Watch, XML, Cloud Computing, Web Scraping, Codeigniter, RESTful, "
    "Stripe, App Design, Kotlin, iOS Development, Full Stack Development, Backend Development, "
    "Push Notification, Sass, RESTful API, React Native, Flutter, GraphQL, "
    "Android App Development, Android Studio, API Development, Microservices, Web Application, "
    "OpenAI, Prompt Engineering, Chatbot Prompt Writing, OpenAI Codex, Azure OpenAI, "
    "AI-Generated Code, AI Chatbot Development, AI Chatbot, AI Mobile App Development, "
    "ChatGPT AI Integration, ChatGPT Prompt"
)


async def collect_criteria(client: FreelancerAPIClient) -> tuple[SearchCriteria, list]:
    """Collect search parameters interactively, run first search, return (criteria, gigs)."""
    print(f"\n{BOLD}── Search Parameters ──────────────────────────────────{RESET}")

    # Env var overrides default; user input overrides env var
    default_skills = os.getenv("DEFAULT_SEARCH_SKILLS", _DEFAULT_SKILLS)
    raw_skills = prompt("Skills (comma-separated)", default_skills)
    skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

    min_budget   = prompt_float("Min budget (USD, leave blank to skip)")
    max_budget   = prompt_float("Max budget (USD, leave blank to skip)")

    print(f"  {DIM}Project type options: fixed_price | hourly | (blank = any){RESET}")
    ptype_raw    = prompt("Project type", "").lower()
    project_type = ptype_raw if ptype_raw in ("fixed_price", "hourly") else None

    limit_raw = prompt("Max results", "10")
    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 10

    score_raw = prompt("Min skill match % (0-100)", "0")
    try:
        min_match = int(score_raw) / 100
    except ValueError:
        min_match = 0.0

    criteria = SearchCriteria(
        skills=skills,
        min_budget=min_budget,
        max_budget=max_budget,
        project_type=project_type,
        min_match_score=min_match,
        limit=limit,
    )

    print(f"\n{YELLOW}🔍 Searching Freelancer.com…{RESET}")
    gigs = await client.search_gigs(criteria)
    return criteria, gigs


def show_results(gigs: list, new_ids: set | None = None) -> None:
    if not gigs:
        print(f"\n{RED}No gigs found. Try broader filters.{RESET}")
        return
    new_ids = new_ids or set()
    label   = f"{GREEN}{BOLD}✅ Found {len(gigs)} gig(s){RESET}"
    if new_ids:
        label += f"  {GREEN}({len(new_ids)} NEW ★){RESET}"
    print(f"\n{label}")
    for i, gig in enumerate(gigs, 1):
        print_gig(i, gig, new=(gig.id in new_ids))
    print(f"\n{DIVIDER}")


def show_detail(gigs: list) -> None:
    if not gigs:
        return
    raw = input(f"\n{CYAN}Enter gig # for full details (or press Enter to skip): {RESET}").strip()
    if not raw:
        return
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(gigs)):
            raise ValueError
    except ValueError:
        print(f"{YELLOW}Invalid selection.{RESET}")
        return

    gig = gigs[idx]
    print(f"\n{DIVIDER}")
    print(f"{BOLD}Title:{RESET}       {gig.title}")
    print(f"{BOLD}Platform:{RESET}    {gig.platform}")
    print(f"{BOLD}Budget:{RESET}      {gig.budget}")
    print(f"{BOLD}Type:{RESET}        {gig.project_type}")
    print(f"{BOLD}Match:{RESET}       {int(gig.match_score * 100)}%")
    print(f"{BOLD}Bids so far:{RESET} {gig.proposals_count}")
    print(f"{BOLD}Client:{RESET}      rating={gig.client_rating}, reviews={gig.client_reviews}")
    print(f"{BOLD}Posted:{RESET}      {gig.posted_date}")
    print(f"{BOLD}Skills:{RESET}      {', '.join(gig.skills_required)}")
    print(f"\n{BOLD}Description:{RESET}")
    print(f"  {gig.description}")
    print(f"\n{BOLD}{GREEN}➡  Place a bid:{RESET}")
    print(f"  {CYAN}{gig.url}{RESET}")
    print(DIVIDER)


# ── Auto-bid ──────────────────────────────────────────────────────────────────

async def auto_bid_gig(client: FreelancerAPIClient, gig) -> dict:
    """Generate an AI proposal and place a bid for a single gig.
    All parameters are read from AUTO_BID_* env vars."""
    llm, llm_error, provider, model = get_llm()
    if not llm:
        return {"success": False, "error": f"Proposal AI unavailable ({provider}/{model}): {llm_error}"}

    name          = os.getenv("AUTO_BID_NAME", "Freelancer")
    skills_raw    = os.getenv("AUTO_BID_SKILLS", "Python")
    skills        = [s.strip() for s in skills_raw.split(",") if s.strip()]
    experience    = int(os.getenv("AUTO_BID_EXPERIENCE", "3"))
    delivery_days = int(os.getenv("AUTO_BID_DELIVERY_DAYS", "7"))
    tone          = os.getenv("AUTO_BID_TONE", "professional")

    # 1. Fetch full project description
    details = await client.get_project_details(gig.id)
    if "error" in details:
        return {"success": False, "error": details["error"]}

    title       = details.get("title", gig.title)
    description = details.get("description", gig.description or "")
    proj_skills = details.get("skills", gig.skills_required or [])
    budget_min  = details.get("budget_min") or 0
    budget_max  = details.get("budget_max") or 0
    avg_bid     = details.get("avg_bid") or 0
    currency    = details.get("currency", "USD")
    bids_count  = details.get("bids_count", gig.proposals_count or 0)

    # 2. Calculate bid amount (range-based percentage of budget_max)
    # Ranges: AUTO_BID_RANGE_<N>=min_usd,max_usd,pct
    # e.g. AUTO_BID_RANGE_1=0,250,95  → bid 95% of budget_max when budget is $0–$250
    def _parse_ranges() -> list:
        ranges = []
        for key, val in os.environ.items():
            if not key.startswith("AUTO_BID_RANGE_"):
                continue
            try:
                parts = [p.strip() for p in val.split(",")]
                rmin, rmax, pct = float(parts[0]), float(parts[1]), float(parts[2])
                ranges.append((rmin, rmax, pct / 100.0))
            except Exception:
                pass
        return sorted(ranges, key=lambda x: x[0])

    _base = budget_max or budget_min or avg_bid or 0
    _matched_pct = None
    for _rmin, _rmax, _pct in _parse_ranges():
        if _rmin <= _base <= _rmax:
            _matched_pct = _pct
            break

    if _matched_pct is not None and _base:
        bid_amount = round(_base * _matched_pct, 2)
    else:
        _fallback_pct = float(os.getenv("AUTO_BID_FALLBACK_PCT", "90")) / 100.0
        bid_amount = round(_base * _fallback_pct, 2) if _base else 50.0

    # 3. Generate AI proposal
    prompt_text = f"""
You are {name}, a senior full-stack & mobile engineer with {experience}+ years experience.

Write a high-conversion Freelancer proposal in a CLEAN, STRUCTURED format.

PROJECT:
{title}

REQUIREMENTS:
{description}

CLIENT CONTEXT (internal use only):
Budget: {currency} {budget_min}-{budget_max}
Current bids: {bids_count} (avg: {currency} {avg_bid:.0f})

YOUR PROFILE:
{name} – {experience}+ years full-stack & mobile engineer
Your bid: {currency} {bid_amount:.0f}
Timeline: {delivery_days} days

---

STRICT RULES:

- Length: 170–220 words AND under 1400 characters
- First paragraph MUST reference the client’s exact problem/use-case
- DO NOT use generic or fluffy openings
- Maintain a clean, structured format with sections (Approach, Features, etc.)
- Keep sentences short, clear, and human
- Include 1–2 concrete technical decisions (stack, architecture, tools)
- Infer technologies from project description (do NOT list random skills)
- Focus on solving the problem, not selling yourself
- Avoid buzzwords, emojis, and repetition

STRUCTURE (MANDATORY):

Start with:
Hi,

Then follow this exact flow:

1. Intro paragraph  
   - Who you are (1 line)  
   - Show you understand THEIR problem  
   - Position yourself as solution  

2. 🔧 Approach  
   - Clear technical approach (stack + reasoning)

3. ✅ Core Features  
   - 4–6 bullet points aligned with project scope  

4. ☁️ Reliability / Performance (or relevant section)  
   - Key engineering decisions / edge cases  

5. 📦 Deliverables  
   - What client gets (concise)

6. 💡 Why Me  
   - 1–2 lines max  
   - Mention past relevant work (e.g., Rhythm) naturally  

7. Ending  
   - Ask ONE smart technical question OR next step  
   - Avoid generic “let’s connect”

STYLE:

- Professional but conversational
- Structured but not robotic
- Each section must add value
- Assume client is technical

CLIENT CONTEXT USAGE:

- Use budget/bids ONLY to adjust tone
- DO NOT mention budget or competitors

OUTPUT:
Only the final proposal text. No explanations.
"""

    try:
        response = llm.invoke(prompt_text)
        content = response.content
        # Some models (e.g. Gemini) return a list of content blocks instead of a plain string
        if isinstance(content, list):
            proposal = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            ).strip()
        else:
            proposal = str(content).strip()
    except Exception as e:
        return {"success": False, "error": f"AI generation failed: {e}"}

    # 4. Submit bid
    result = await client.place_bid(
        project_id=gig.id,
        amount=bid_amount,
        period=delivery_days,
        description=proposal,
    )
    result["proposal"]   = proposal
    result["bid_amount"] = bid_amount
    result["title"]      = title
    result["ai_provider"] = provider
    result["ai_model"] = model
    return result


async def auto_poll(client: FreelancerAPIClient, criteria: SearchCriteria,
                    interval: int, seen_ids: set, auto_bid: bool = False) -> None:
    """
    Poll Freelancer.com every `interval` seconds using the same criteria.
    Prints only NEW gigs (not seen before). Press Ctrl+C to stop.
    """
    print(f"\n{GREEN}{BOLD}⏱  Auto-polling every {interval}s — Press Ctrl+C to stop{RESET}\n")

    poll_count = 0
    try:
        while True:
            await asyncio.sleep(interval)
            poll_count += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"{DIM}[{now}] Poll #{poll_count} — checking for new gigs…{RESET}", end=" ", flush=True)

            # Disable TTL cache for fresh results each poll
            client.cache.clear()

            gigs = await client.search_gigs(criteria)

            new_gigs = [g for g in gigs if g.id not in seen_ids]

            if not new_gigs:
                print(f"{DIM}no new gigs.{RESET}")
            else:
                print(f"\n{GREEN}{BOLD}🚨 {len(new_gigs)} NEW GIG(S) FOUND!{RESET}")

                # ── All notification channels (desktop + mobile) ──────────────
                for gig in new_gigs:
                    await send_all_notifications(gig)

                # ── Auto-bid on qualifying new gigs ───────────────────────────
                if auto_bid:
                    min_match    = int(os.getenv("AUTO_BID_MIN_MATCH", "60")) / 100
                    max_per_poll = int(os.getenv("AUTO_BID_MAX_PER_POLL", "3"))
                    candidates   = [g for g in new_gigs if g.match_score >= min_match][:max_per_poll]
                    for gig in candidates:
                        print(f"{YELLOW}  🤖 Auto-bidding: {gig.title[:55]}…{RESET}", flush=True)
                        bid_result = await auto_bid_gig(client, gig)
                        if bid_result.get("success"):
                            print(f"{GREEN}  ✅ Bid placed! "
                                  f"Amount: {bid_result.get('bid_amount')} | "
                                  f"ID: {bid_result.get('bid_id')}{RESET}")
                        else:
                            print(f"{RED}  ❌ Bid failed: {bid_result.get('error')}{RESET}")

                for gig in new_gigs:
                    print_gig("NEW", gig, new=True)
                    seen_ids.add(gig.id)
                print(f"\n{DIVIDER}")

                # Prompt to view details — auto-skips after 10 s so poll continues
                raw = timed_input("View a new gig? Enter # from above list (or Enter to continue)", timeout=10)
                if raw.isdigit():
                    idx = int(raw) - 1
                    if 0 <= idx < len(new_gigs):
                        show_detail([new_gigs[idx]])

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⏹  Auto-poll stopped.{RESET}")


async def main() -> None:
    print_header()

    client = FreelancerAPIClient()
    if not client.authenticate():
        print(f"{RED}❌ Authentication failed. Check FREELANCER_OAUTH_TOKEN in {_env_file}{RESET}")
        return

    print(f"{GREEN}✅ Connected to Freelancer.com{RESET}")

    while True:
        criteria, gigs = await collect_criteria(client)
        seen_ids = {g.id for g in gigs}

        show_results(gigs)
        show_detail(gigs)

        # ── Auto-poll option ────────────────────────────────────────────────
        poll_raw = prompt(
            "\nAuto-refresh interval in seconds (e.g. 60), or Enter to skip", ""
        )
        if poll_raw.isdigit() and int(poll_raw) > 0:
            auto_bid_enabled = os.getenv("AUTO_BID_ENABLED", "false").lower() == "true"
            if auto_bid_enabled:
                print(f"\n{YELLOW}⚠  Auto-bidding is ENABLED (AUTO_BID_ENABLED=true){RESET}")
                confirm = input(f"{CYAN}Confirm: auto-place bids on new gigs? (y/n): {RESET}").strip().lower()
                auto_bid_enabled = (confirm == "y")
                if auto_bid_enabled:
                    choose_auto_bid_ai()
            await auto_poll(client, criteria, interval=int(poll_raw),
                            seen_ids=seen_ids, auto_bid=auto_bid_enabled)

        again = input(f"\n{CYAN}New search? (y/n): {RESET}").strip().lower()
        if again != "y":
            break

    print(f"\n{DIM}Goodbye!{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())

