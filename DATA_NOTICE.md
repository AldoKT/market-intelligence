# Data & Secret Notice

SIGNAL was developed using Sectors-derived market data.

Before publishing this repository publicly:

1. **Never commit API keys**. Keep them in local environment variables or `.env` files.
2. Raw API responses and caches remain excluded by default. The explicitly approved SIGNAL pilot, October OOS, and Phase2 broker packages are tracked as narrow exceptions to support offline reproduction; they contain Sectors-derived data, including reviewed raw responses.
3. This repository contains derived research CSVs and historical demo payloads so collaborators can reproduce the current prototype without API usage.
4. Confirm that your Sectors plan/terms permit redistribution of any derived or cached data before making the repository public. If uncertain, use a private repository and distribute data separately.
5. The legacy demo is dated 9 Sep 2026. The accepted pilot SIGNAL snapshot is 30 Sep 2026; the separately labelled broker/OOS research extends to 6 Oct 2026. None must be presented as live market data.
