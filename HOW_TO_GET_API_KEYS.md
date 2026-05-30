# How to get API keys for VerbaTrust

Add these to `backend/.env` (copy from `backend/.env.example`).

---

## 1. AI/ML API — primary LLM
Used for: hedging scoring, spin-vs-reality checks

1. Go to **https://aimlapi.com**
2. Sign up / log in
3. Dashboard → API Keys → Create key
4. Copy into `AIML_API_KEY=`

The app works rule-based offline without this key.

---

## 2. Featherless AI — cheap bulk inference
Used for: condensing long transcripts before scoring (saves tokens)

1. Go to **https://featherless.ai**
2. Sign up / log in  
3. Account → API Key
4. Copy into `FEATHERLESS_API_KEY=`
5. Promo code on sign-up: **WEBDATA26**

The app passes transcripts through unsummarized without this key.

---

## 3. Cognee — knowledge-graph memory
Used for: cross-quarter diffs (what did management stop saying?)

1. Go to **https://cognee.ai**
2. Sign up / log in
3. Settings → API Keys → Generate
4. Copy into `COGNEE_API_KEY=`
5. Promo code: **WEBDATA26**

The app uses a local `cognee_data/quarters.json` file without this key.

---

## 4. Bright Data — live web scraping
Used for: live earnings transcripts past paywalls, news/jobs/filings signals

1. Go to **https://brightdata.com**
2. Sign up → redeem promo code **unlocked** (free credits)
3. Dashboard → Account → API Token
4. Copy into `BRIGHTDATA_API_KEY=`

The app reads from `sample_data/` without this key (full offline demo).

---

## After filling in the keys

```bash
cd backend
cp .env.example .env
# fill in the keys above
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open the frontend and point it at `http://localhost:8000`.
