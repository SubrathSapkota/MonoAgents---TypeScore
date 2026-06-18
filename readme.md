PHASE 1 — Build the Scanner Only
    Step 1 — Setup FastAPI Backend (done)
    Step 2 — Create Website Scanner (done) 
PHASE 2 — Add Lighthouse (done)
PHASE 3 — Accessibility Scan
    Using axe-core
    Goal: accessibility violations
    Especially:
        contrast
        text readability
        zoom/scaling issues
    Easiest Approach: Inject axe into Playwright page.(axe.run())
    Output Example:
    {
        "violations": [
            {
            "type": "color-contrast",
            "count": 5
            }
        ]
    }
PHASE 4 — PDF Scanner (just ignore this for now just do the website)
PyMuPDF
output:
{
  "pdf": "annual-report.pdf",
  "fonts": [
    "HelveticaNeue",
    "ArialMT"
  ]
}
PHASE 5 — Scoring Engine (main focus)
Now combine everything.
This is the HEART of the product.

    Final Composite
    Final Score=(0.2×B)+(0.3×L)+(0.2×P)+(0.15×A)+(0.15×D)
    Where:
        B = Brand consistency
        L = License compliance
        P = Performance
        A = Accessibility
        D = Developer experience
PHASE 6 — Frontend Dashboard
NOW build UI.
Required Dashboard Sections
1. URL Input
2. Overall Score
3. Metric Breakdown
    Cards:
        Brand consistency
        Accessibility
        Performance
        Licensing
        Developer experience
4. Violations List
Unauthorized font detected: Arial
    Found on:
    /pricing
    /docs

Recommended UI Style

You mentioned:

minimal
enterprise
NYTimes-like

Perfect for this.

Typography-focused product should look:

clean
premium
whitespace-heavy



cd /Users/subratshapkota/Developer/Hackathon-2026/backend

# Activate the existing virtualenv (or create one — see below)
source .venv/bin/activate

# Install Python deps (if not already done)
pip install -r requirements.txt

# Install Playwright browsers (required for /scan and accessibility checks)
playwright install chromium

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

uvicorn app.main:app --reload --port 8000
