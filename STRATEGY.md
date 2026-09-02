# Greenscape Pro — AI Agent Strategy
**Prepared for isthispossible.ai take-home | Muhammad Aqib**

Marcus's stated priority order (quoting → follow-up → crew coaching → marketing) gets the top item right but the rest wrong. Crew coaching is real money but an order of magnitude below the real lever. Marketing is solving a problem he explicitly says doesn't exist: *"Quote [constrained]. I cannot keep up with the leads I have."* I ranked by dollar leverage and structural dependency, not by what was said out loud first.

## 1. Quote & Proposal Accelerator — *P0, building this*
**Purpose:** Turn Marcus's raw site-walk notes into a structured, priced proposal draft in minutes, not days.

- Parses free-text site-walk notes against the existing pricing catalog (200+ line items)
- Auto-flags any proposal over $30K for Carlos's render step (matches current rule)
- Produces a structured line-item draft Marcus reviews and approves, not sends blind
- Routes approved proposals into the existing send flow (Slack notification as the trigger)

**What it unblocks:** Marcus is the bottleneck by his own admission — *"I have to touch every proposal... nobody else knows how to do that."* This removes the interpretation step, not the judgment step.

**ROI:** 35–40% of qualified leads are lost to faster competitors during a 6–9 day quote cycle, on ~150 projects/year at $28K average. Even a partial recovery (say, half the lost deals from cutting cycle time to 1–2 days) is worth well over $1M/year in recoverable revenue — this dwarfs every other lever in the business.

**Why #1:** Marcus said "speed up quoting" — true, but vague enough that a naive build might target the wrong layer (a chatbot, a CRM tweak). The actual bottleneck is narrower: converting his own notes into a priced scope. That's the specific system worth building, not "quoting" in the abstract.

## 2. Post-Sign Milestone Tracker
**Purpose:** Automate the HOA/permit/deposit chase that currently stalls 8–12 projects at once.

- Tracks each signed project through HOA submission, permit status, and deposit payment
- Sends automated reminder sequences to customers and internal nudges to Jenna
- Escalates to a human only when a stage stalls past a defined threshold

**What it unblocks:** Jenna's manual chasing, and the 2–3 week compounding delay that pushes crew scheduling.

**ROI:** 8–12 projects in limbo at $28K average = $224K–$336K in delayed revenue at any given moment. This isn't new revenue, it's revenue arriving faster — second only to the quote cycle in scale.

## 3. Build-Progress Update Agent
**Purpose:** Auto-generate Marcus-voiced progress updates from CompanyCam/Jobber milestones.

- Triggers on photo uploads or Jobber check-ins
- Drafts a short, personal-sounding update Marcus can approve and send in one tap
- Replaces the "silence for 4–5 days → anxious customer calls Jenna" pattern

**What it unblocks:** Marcus already knows this works — *"the Looms: when I do send them, customers love it... I've gotten referrals"* — he just can't keep up (30% coverage today). This is a low-cost, high-signal fix on something already proven to work.

## 4. Closed-Lost Lead Reactivation Agent
**Purpose:** Personalized, Marcus-voiced re-engagement on the 1,400+ closed-lost lead pile.

- Pulls context from existing GHL notes per lead
- Drafts individualized "still thinking about your backyard?" style messages, not mass blasts
- Sends via GHL SMS/email with Marcus's approval

**ROI:** Even a conservative 2% reclose on 1,400 leads at $28K average is $784K in latent revenue. Ranked below #1–3 because it's the least structurally urgent — this pile isn't decaying further if left one more quarter, unlike the active bottlenecks above it.

## 5. Lead Pre-Qualification Agent
**Purpose:** Filter obviously unqualified leads before they hit Marcus's calendar.

- SMS or voice bot asks 4–5 qualifying questions (budget range, timeline, ownership status)
- Routes only qualified leads to Marcus's call queue

**ROI:** Smallest in isolation (1–2 hrs/week saved), but it's included because it protects the input to #1 — cleaner leads mean less wasted time before the highest-leverage system even engages. Systemically, this sits upstream of the whole chain: **5 → 1 → 2 → 3**, with 4 recycling anyone who falls out back to the top.

---

### Why #1 isn't simply the founder's stated #1
Marcus's stated priority is directionally right but operationally vague. "Speed up quoting" could mean a dozen different builds. The data says the actual constraint is a single, specific interpretation step that only Marcus can currently perform — that's the system worth automating, and it's narrower than what "quoting" would suggest to most people building from the transcript alone.

### What I excluded, and why
**The marketing/content agent** (Marcus's stated #4). He states outright, twice, that lead volume is not his constraint — ROAS is healthy at 4–4.5x and he "cannot keep up with the leads I have." Building a marketing agent here optimizes a metric that isn't the bottleneck. It's a clean, evidence-backed "no."

### System Architecture Trade-offs & Scaling Bottlenecks
- **What breaks first at scale:** Full pricing catalog in-context prompting works reliably up to ~200 items. Beyond ~500 items, token costs rise, latency increases, and LLM attention drift degrades SKU matching accuracy.
- **Production solution for scale:** Upgrade from full catalog in-context prompting to a two-stage Vector RAG pipeline (using OpenAI `text-embedding-3-small` or pgvector in Supabase) to dynamically retrieve top 15 relevant line items before generation.
- **What I'd do with more time:** Implement direct GoHighLevel (GHL) SMS API webhooks for native customer proposal delivery, and line-item confidence scoring to auto-highlight uncertain estimates for Marcus's review.
