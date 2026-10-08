# Static demo on GitHub Pages

This build uses existing derived JSON for 28 stocks. It does not run Python/FastAPI on the website or make Sectors API requests. JSON shipped with the demo is publicly downloadable. Credentials and raw fetch ledgers are excluded.

## Publish

1. In the GitHub repository, open **Settings > Pages** and choose **GitHub Actions** as the Source.
2. Commit the static-demo changes and push `main`.
3. Wait for **Actions > Deploy SIGNAL static demo** to finish. The deployment link appears in the run and in Settings > Pages.

Expected URL: https://aldokt.github.io/market-intelligence/

The workflow builds from the committed payloads and broker checkpoint archive. No backend, API key, pandas, or paid API request is needed.

## Local preview

From `frontend`:

```powershell
npm ci
npm run build:pages
npm run preview:pages -- --port 5185
```

Open http://127.0.0.1:5185/market-intelligence/

Pages uses hash routes, so stock detail URLs can be refreshed directly. The regular `npm run dev` mode continues using the local backend. Watchlist preferences are stored in each visitor's browser; the demo does not sync them across devices. Data remains fixed until a new build is published.

If the repository name changes, update `VITE_PAGES_BASE` in `frontend/.env.pages`.
