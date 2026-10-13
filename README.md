# PlotWorth

Real-time housing price prediction and neighborhood affordability clustering across Indian localities.

PlotWorth is a single-page dashboard that lets a user search any Indian locality and instantly view live real-estate metrics, predictive price forecasts, K-Means affordability clusters on a Leaflet map, statistical comparisons with nearby localities, and model evaluation metrics.

## Stack

- Frontend: HTML5, CSS3, vanilla JavaScript ES6, Leaflet.js, Plotly.js (Netlify)
- Backend: Python 3.11, FastAPI, httpx, pandas, scikit-learn (Render free tier)
- Analytics: R Shiny with ggplot2, plotly, dplyr, DT

No React, Vue, Tailwind, or build tool. No AI or LLM features.

## Local Development (Windows, PowerShell)

Backend:

    cd backend
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install -r requirements.txt
    python generate_dataset.py
    uvicorn backend:app --reload --port 8000

Frontend:

    cd frontend
    python -m http.server 5500

## Deployment

1. Create a new GitHub repository named PlotWorth. Do not initialize with README, .gitignore, or license.
2. Clone locally, add all files, and push to main.
3. Go to render.com, create a new Web Service, connect the repository, set Root Directory to `backend`, Language to Python 3, Build Command to `pip install --upgrade pip && pip install -r requirements.txt`, Start Command to `uvicorn backend:app --host 0.0.0.0 --port $PORT`, and add the `PYTHON_VERSION` environment variable set to `3.11.9`.
4. Wait for the Render build to succeed. Copy the public URL.
5. Open `frontend/script.js` and replace the `BACKEND_BASE` constant with the Render URL. Commit and push.
6. Go to netlify.com, import the repository, set Base Directory to `frontend`, leave Build Command blank, set Publish Directory to `frontend`. Deploy.
7. Open the Netlify URL and search for "Whitefield Bangalore" to verify.
8. Do not include a `netlify.toml` file.