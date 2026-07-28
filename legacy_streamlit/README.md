# Legacy Streamlit App (archived)

This folder contains the **original Streamlit + PyTorch** version of Bird
Population Decline AI, kept intact for reference and local use.

> ⚠️ This version **cannot** be deployed on Vercel — Streamlit needs a
> persistent WebSocket server, which serverless platforms don't provide, and
> `torch`/`rasterio` exceed Vercel's function size limits. The production app
> now lives at the repository root as a static frontend + Python serverless API.

## Run it locally

```bash
cd legacy_streamlit
python -m venv venv
venv\Scripts\activate        # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
streamlit run app.py
```

Note: `app.py` originally contained hard-coded API keys. Those keys are exposed
in git history and **should be rotated**. The new app reads all secrets from
environment variables instead.
