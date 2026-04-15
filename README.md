# Morning Edition 📰

A daily AI-curated magazine built from Hacker News, styled like a real editorial publication. Every morning at 7am, it fetches the front page, runs Claude to curate the 10 stories that fit your taste, and renders each as a distinct magazine spread — then pushes to GitHub Pages and pings you on Telegram.

---

## How it works

```
7:00 AM  →  GitHub Actions wakes up
             ↓
         Fetches HN top 40 stories
             ↓
         Claude curates top 10, writes headlines, summaries, flags actionable ones
             ↓
         Python renders a 12-section HTML magazine (cover + 10 spreads + colophon)
             ↓
         Commits magazines/YYYY-MM-DD.html + updates magazines/index.html
             ↓
         GitHub Pages serves it at your-username.github.io/repo/magazines/YYYY-MM-DD.html
             ↓
         Telegram bot sends you the link
```

---

## One-time setup (15 minutes)

### Step 1 — Create your GitHub repo

1. Go to [github.com/new](https://github.com/new)
2. Name it something like `morning-edition` (public or private, both work)
3. **Don't** initialize with a README — keep it empty
4. Click **Create repository**

Push this project to it:
```bash
cd morning-edition
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/morning-edition.git
git branch -M main
git push -u origin main
```

### Step 2 — Enable GitHub Pages

1. In your repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)`
4. Save. Your site will be at:
   `https://YOUR_USERNAME.github.io/morning-edition/`

### Step 3 — Create a GitHub Personal Access Token (PAT)

The workflow needs to push commits back to the repo.

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. **Generate new token (classic)**
3. Name: `morning-edition-push`
4. Expiration: 1 year (or No expiration)
5. Scopes: check **repo** (full control)
6. **Generate token** — copy it now, you won't see it again

### Step 4 — Get your Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. **API Keys** → **Create Key**
3. Copy the key

### Step 5 — Create your Telegram bot

You'll need a **bot token** and your personal **chat ID**.

**Create the bot:**
1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Give it a name (e.g. `Morning Edition`)
4. Give it a username (e.g. `my_morning_edition_bot`)
5. BotFather replies with your token: `123456789:ABCdef...` — copy it

**Get your chat ID:**
1. Search for and open your new bot
2. Send it any message (e.g. `hello`)
3. Visit this URL in your browser (replace with your token):
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
4. Look for `"chat":{"id":YOUR_CHAT_ID}` — that number is your chat ID

**Test it:**
```bash
curl -s "https://api.telegram.org/botYOUR_TOKEN/sendMessage" \
  -d chat_id=YOUR_CHAT_ID \
  -d text="Morning Edition bot is alive 👋"
```

### Step 6 — Add secrets to GitHub

In your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these four:

| Secret name | Value |
|---|---|
| `GH_PAT` | Your personal access token from Step 3 |
| `ANTHROPIC_API_KEY` | Your Anthropic API key from Step 4 |
| `TELEGRAM_BOT_TOKEN` | Your bot token from Step 5 |
| `TELEGRAM_CHAT_ID` | Your chat ID from Step 5 |

### Step 7 — Run it manually to test

1. Repo → **Actions** tab
2. Click **Morning Edition** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Watch the logs — it should take ~30 seconds
5. Check `magazines/` in your repo for a new HTML file
6. Check Telegram for your notification

---

## Timezone adjustment

The cron is set to `0 14 * * *` (7am PDT, summer). Adjust for your timezone:

| Time | Cron |
|---|---|
| 7am PDT (summer) | `0 14 * * *` |
| 7am PST (winter) | `0 15 * * *` |
| 7am EST | `0 12 * * *` |
| 7am GMT | `0 7 * * *` |

Edit `.github/workflows/morning-edition.yml` and update the cron line.

---

## Customizing your taste

Edit the `TASTE PROFILE` section in `generate_magazine.py` inside the `curate()` function. The three lines starting with `LOVE:`, `LIKE:`, and `SKIP:` are plain English — just update them to match what you actually want to read.

---

## File structure

```
morning-edition/
├── generate_magazine.py        ← main script
├── requirements.txt
├── .nojekyll                   ← tells GitHub Pages not to run Jekyll
├── .github/
│   └── workflows/
│       └── morning-edition.yml ← the daily cron job
└── magazines/
    ├── index.html              ← auto-generated archive page
    ├── manifest.json           ← auto-generated issue list
    └── 2025-01-15.html         ← each day's magazine
```

---

## URLs

- **Today's issue:** `https://YOUR_USERNAME.github.io/morning-edition/magazines/YYYY-MM-DD.html`
- **Archive:** `https://YOUR_USERNAME.github.io/morning-edition/magazines/`

---

## Cost

Each run makes one Claude API call (claude-opus-4-5, ~2K input + ~1.5K output tokens). At current pricing that's roughly **$0.03–0.05 per issue**, or ~$1/month. GitHub Actions is free for public repos.
