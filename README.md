# Mumble

A voice-powered speech practice app for children with speech delays.

Mumble is a friendly pet you teach to speak. Each practice session warms up
with easy words for your target sound, then builds up to the day's target word —
said nice and slow. Kids earn XP, keep daily streaks, and climb a friendly league.

## Choose your pet

Kids pick a 🦄 unicorn or 🐉 dragon at signup (or anytime in Settings). The pet
grows through five stages as XP climbs — starting as an egg, hatching, and
growing into a full creature with wings, mane, and more.

## AI feature

**AI Word Coach** — inside a practice session, tap the **✨ AI Word Coach** button
on the "Today's word" bar. Using OpenAI **gpt-5.4-nano** (server-side, via the
Responses API), Mumble generates a fresh, age-appropriate practice set for your
target sound and current pet level: three easy warm-up words, one bigger target
word, and a cheerful coaching sentence (read aloud) reminding you to say it slowly.

Run it locally (key stays on the server, never in the browser):

```bash
python3 -m pip install -r requirements.txt "openai>=1.99"   # only python-dotenv/certifi are needed to run
# put your key in a .env file (gitignored):
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-5.4-nano
PORT=5187 python3 server.py
```

Then open **http://127.0.0.1:5187** in your browser. The same server serves the
app and proxies the `/api/word-coach` call so the API key stays server-side.

## Download

Get the latest release from the [Releases page](https://github.com/Prayan-AIML/mumble/releases).

Available for macOS (.dmg), Windows (.exe), and Linux.

## Latest Build

[v1.0.21 — Reliable XP saving, scrolling fix, fitted window, pet choice](https://github.com/Prayan-AIML/mumble/actions/runs/28279235677)

See all builds on the [Actions page](https://github.com/Prayan-AIML/mumble/actions).
