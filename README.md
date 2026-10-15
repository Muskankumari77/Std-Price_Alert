# PricePilot AI — Wissen Price Alert Workspace

Local dashboard in the original dark-green, orange and warm-cream visual theme. It includes the Wissen command-line assessment tool, JWT-protected administrator sign-in, CSV/XLSX data import, rule-based price alerts and an optional Groq-powered AI copilot.

## Run in VS Code

1. Install Python 3.10+ and extract the ZIP.
2. Open this folder in VS Code.
3. Install the Excel reader dependency: `python -m pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:8000`.
6. Demo admin login: username `admin`, password `Admin@12345`. Change these before any shared/public deployment using `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `JWT_SECRET` environment variables. This is a local assessment/demo setup, not a production security review.

## Use the supplied datasets

- **Amazon(1).csv**: use the Data Import page's **Use Amazon dataset** button, or upload your own Amazon export. It maps `OrderDate`, `ProductID`, and `UnitPrice` to daily average prices, with instrument IDs such as `AMZ-P00014`.
- **Online Retail(4).xlsx**: use **Use Online Retail dataset**, or upload the workbook. It maps `InvoiceDate`, `StockCode`, and positive `UnitPrice` values to daily average prices, with IDs such as `OR-85123A`.
- **Standard alert CSV**: accepts `date,instrument,close`.

The two packaged daily datasets were derived from the supplied files. They are processed price-series CSVs, not the original raw files. For each product/stock code and calendar date, the tool averages the applicable unit-price rows. Online Retail zero/negative unit prices are skipped for this price series. This mapping is a pragmatic assessment adapter, not an assertion that retail unit price is a traded financial close.

## Alert rules and CLI

Rules are JSON objects. Example: `{"id":"r1","instrument":"AMZ-P00014","type":"level","direction":"below","level":100}`. Supported types: `level` and `ma_cross`; direction: `above` or `below`. Level alerts trigger on a crossing, not every day below/above. Moving averages require complete windows.

CLI required by the brief: `python alerts.py data/prices.csv rules.json`. Output is ordered by date then rule ID.

## Tests

Run `python -m unittest discover -s tests -v`. The included suite tests level crossings, moving-average warm-up/crossing, ordering, invalid dates/prices, duplicate records and invalid rules. Add your own tests for the assessment dataset and personally inspect results before submission.

## Admin authentication

The dashboard login creates an HS256-signed JWT with an 8-hour expiry. Protected endpoints require a bearer token. Local defaults exist only to make the downloaded assessment demo runnable. Set strong environment variables before sharing the app. The app is bound to `127.0.0.1` by default.

## AI copilot

The copilot works in local fallback mode without a key, summarizing the current analysis and suggesting verification steps. For generative answers, set `GROQ_API_KEY` in your shell environment and restart the server; `GROQ_MODEL` can override the default `llama-3.3-70b-versatile`. If configured, the question and a small summary of alert results are sent to Groq. Never put an API key in frontend JavaScript or commit it to Git.

Example PowerShell setup for the current terminal:

```powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="choose-a-strong-password"
$env:JWT_SECRET="paste-a-long-random-secret-here"
$env:GROQ_API_KEY="your-groq-api-key"  # optional
python app.py
```

## AI-use and verification note

AI assistance was used to develop the dashboard, file adapters, JWT demo authentication, copilot integration and tests. Review the code, run the test suite and verify imported dataset mappings yourself. Document any additional mistakes you discover and the fixes you make; do not claim checks you have not performed.
