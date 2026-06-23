# Mumble — project handoff prompt

Copy everything below this line and paste it into Google Antigravity as your first message.

---

## Context

I'm Prayan, a student at the GenWise AI/ML camp (June 2026). Over the past week I learned: Claude API + tool calling, Supabase (database + auth + storage), git → GitHub → Vercel deployment, Web Speech API, computer vision basics, JSON tool calls, and full-stack web apps. I've been brainstorming a project and have a working prototype. I need you to help me continue building it.

---

## The project: Mumble

A voice-powered speech-practice app for children with speech delays. The core idea: a creature called Mumble grows as the child's speech improves. The child and Mumble are on the same journey — not a patient being corrected.

**Three core pillars:**
1. Creature that grows when you speak — starts as an egg, evolves through 5 stages (Egg → Hatching → Hatchling → Fledgling → Speaker), powered by XP earned through practice
2. Real-world quests — Mumble assigns missions the child does in real life ("say this word to your mum today"), parent confirms in the app, child gets bonus XP
3. Detects frustration and adapts — detects frustrated tone/words, Mumble's eyes droop, response tone softens, switches to easier exercises

**Business model:**
- Free: daily practice + creature growth
- Paid (₹299/month): parent dashboard + weekly therapist reports
- B2B: sell to speech clinics in India where therapists are scarce

**Positioning:** fills the gap between weekly therapy sessions. Never diagnoses. Always "practice + encouragement, reports for your therapist to interpret."

---

## What's already built

A working single-file HTML prototype at: `mumble-prototype/index.html`

**What it does right now:**
- Setup screen: enter child's name, no API key needed
- Requests mic permission once silently on startup (no repeated prompts)
- Voice loop: tap mic → Web Speech API records → response chosen from pre-written pool → spoken back via Web Speech Synthesis (pitch 1.3, rate 0.88 for cute voice)
- Creature SVG with 5 stages, dynamically drawn with mood variants (normal, happy, tired, listening, speaking)
- XP system with smooth progress bar, evolves at 40 / 100 / 200 / 350 XP
- Sparkle canvas animation on evolution
- Frustration detection: short inputs, keywords (stop/ugh/hard/can't), or frustration level ≥ 2 → switches to easy response pool + tired mood
- Streak dot appears after 3 good responses in a row
- Quest system: triggers every 4 rounds, overlay card shown, child accepts, quest saved to localStorage
- Parent panel: slide-up sheet showing stage, XP, quests completed, active quest with "confirm done" button
- Typing fallback if mic unavailable
- localStorage persistence (XP, stage, active quest survive page refresh)
- 4 sounds to practise: R, S, TH, L — each with 8 normal responses + 3 easy responses
- 4 quests per sound (child-facing + parent-facing text)

**Tech used:** pure HTML/CSS/JS, Web Speech API (SpeechRecognition + SpeechSynthesis), Canvas API for sparkles, localStorage. No backend yet.

---

## What needs to be built next

### Priority 1 — make it actually good
- [ ] Replace pre-written responses with real Claude API responses (model: claude-sonnet-4-6). System prompt: Mumble is the student, child is the teacher. Max 2 sentences. End every reply with a challenge. Never say "wrong". Keep API key on a backend (Supabase edge function), not in the browser.
- [ ] Better creature design — currently SVG ellipses, should feel more like a real character
- [ ] Sound detection — actually check if the child is attempting the target sound, not just "they said something"
- [ ] Animated mouth when Mumble speaks (sync with TTS)

### Priority 2 — backend (Supabase)
- [ ] Supabase database: tables for `children` (id, name, stage, xp), `attempts` (child_id, sound, transcript, timestamp, xp_earned), `quests` (child_id, quest_text, completed, completed_at)
- [ ] Supabase Auth: parent login (email/password or Google OAuth)
- [ ] Weekly report generation: agent reads last 7 days of attempts, generates a summary PDF the parent can share with therapist
- [ ] Supabase edge function as Claude API proxy (keeps API key server-side)

### Priority 3 — product polish
- [ ] Onboarding flow: which sounds to target, child's age, connected to a therapist yes/no
- [ ] Daily streak (separate from session streak) — Mumble looks sad if not practised in 24h
- [ ] Multiple children per parent account
- [ ] Paywall: free = 10 minutes/day + basic creature, paid = unlimited + parent dashboard + reports

---

## Files in the project

```
GENWISE aiml/
├── mumble-prototype/
│   ├── index.html          ← the working prototype (all-in-one)
│   └── ANTIGRAVITY-HANDOFF.md  ← this file
└── class-transcripts/
    └── project-ideas.md    ← all 3 brainstormed ideas with pros/cons
```

---

## Other ideas I brainstormed (on the back burner)

1. **Palette** — AI stylist for colourblind adults. Photos your wardrobe, suggests daily outfits, shopping assistant. Vision + agent + Supabase. ₹299/month + affiliate.
2. **Spark** — Two-player sign language game where a hearing child and deaf child unlock a story together by communicating in sign. Vision (sign recognition) + real-time multiplayer. Harder to build.

---

## My constraints

- Student, building for the first time
- Want something that actually helps people AND is profitable
- Target users: parents of children with speech delays in India (not tech-savvy, never used AI)
- India-first: Hindi/regional language support matters eventually
- Keep it simple enough to ship, ambitious enough to be interesting

---

## First task for you

Read the existing `index.html` prototype, then help me:
1. Set up a Supabase project with the right schema for Mumble
2. Move the app toward a proper multi-file structure (HTML + JS + CSS separated, or a simple Vite project)
3. Add the Claude API via a Supabase edge function so responses are real AI, not pre-written

Start by reading the prototype file and asking me any clarifying questions before you touch anything.
