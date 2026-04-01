#!/usr/bin/env python3
"""
Interactive Freelancer.com Gig Search

Usage:
    APP_ENV=dev python search_gigs.py
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env based on APP_ENV
_app_env = os.getenv("APP_ENV")
_env_file = f".env.{_app_env}" if _app_env else ".env"
if Path(_env_file).exists():
    load_dotenv(_env_file, override=True)

from freelance_api_clients import FreelancerAPIClient, SearchCriteria


# ── ANSI colours ─────────────────────────────────────────────────────────────
BOLD  = "\033[1m"
CYAN  = "\033[96m"
GREEN = "\033[92m"
YELLOW= "\033[93m"
RED   = "\033[91m"
DIM   = "\033[2m"
RESET = "\033[0m"

DIVIDER = f"{DIM}{'─' * 64}{RESET}"


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


def print_gig(index: int, gig) -> None:
    """Print a single gig in a readable card format."""
    title       = gig.title or "Untitled"
    budget      = gig.budget or "N/A"
    ptype       = (gig.project_type or "").upper()
    match_pct   = int(gig.match_score * 100)
    proposals   = gig.proposals_count or 0
    rating      = f"{gig.client_rating:.1f} ⭐" if gig.client_rating else "No rating"
    skills      = ", ".join(gig.skills_required) if gig.skills_required else "N/A"
    desc        = (gig.description or "").strip()
    short_desc  = (desc[:200] + "…") if len(desc) > 200 else desc
    url         = gig.url or "N/A"

    print(f"\n{DIVIDER}")
    print(f"  {BOLD}#{index}  {title}{RESET}")
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


async def run_search(client: FreelancerAPIClient) -> list:
    """Collect search parameters interactively and return results."""
    print(f"\n{BOLD}── Search Parameters ──────────────────────────────────{RESET}")

    # Skills
    raw_skills = prompt("Skills (comma-separated)", "Python, Django")
    skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

    # Budget
    min_budget = prompt_float("Min budget (USD, leave blank to skip)")
    max_budget = prompt_float("Max budget (USD, leave blank to skip)")

    # Project type
    print(f"  {DIM}Project type options: fixed_price | hourly | (blank = any){RESET}")
    ptype_raw = prompt("Project type", "").lower()
    project_type = ptype_raw if ptype_raw in ("fixed_price", "hourly") else None

    # Limit
    limit_raw = prompt("Max results", "10")
    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 10

    # Min match score
    score_raw = prompt("Min skill match % (0-100)", "0")
    try:
        min_match = int(score_raw) / 100
    except ValueError:
        min_match = 0.0

    print(f"\n{YELLOW}🔍 Searching Freelancer.com…{RESET}")

    criteria = SearchCriteria(
        skills=skills,
        min_budget=min_budget,
        max_budget=max_budget,
        project_type=project_type,
        min_match_score=min_match,
        limit=limit,
    )

    gigs = await client.search_gigs(criteria)
    return gigs


def show_results(gigs: list) -> None:
    if not gigs:
        print(f"\n{RED}No gigs found. Try broader filters.{RESET}")
        return

    print(f"\n{GREEN}{BOLD}✅ Found {len(gigs)} gig(s){RESET}")
    for i, gig in enumerate(gigs, 1):
        print_gig(i, gig)
    print(f"\n{DIVIDER}")


def show_detail(gigs: list) -> None:
    """Let user pick a gig to see full description + URL to place a bid."""
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


async def main() -> None:
    print_header()

    client = FreelancerAPIClient()
    if not client.authenticate():
        print(f"{RED}❌ Authentication failed. Check FREELANCER_OAUTH_TOKEN in {_env_file}{RESET}")
        return

    print(f"{GREEN}✅ Connected to Freelancer.com{RESET}")

    while True:
        gigs = await run_search(client)
        show_results(gigs)
        show_detail(gigs)

        again = input(f"\n{CYAN}Search again? (y/n): {RESET}").strip().lower()
        if again != "y":
            break

    print(f"\n{DIM}Goodbye!{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
