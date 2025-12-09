# Backend Deployment Guide (Render)

## Quick Deploy

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **New +** → **Web Service**
3. Connect your GitHub account and select the `websapdev/vs` repository
4. Render will auto-detect the `render.yaml` configuration
5. Click **Create Web Service**

## Manual Configuration (if auto-detect fails)

- **Name**: vysalytica-api
- **Environment**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `PYTHONPATH=. gunicorn api:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`

### Environment Variables

Set these in the Render dashboard:

```
DATABASE_URL=sqlite:///api/data/vysalytica.db
FLASK_ENV=production
SECRET_KEY=<generate-a-random-secret-key>
JWT_SECRET_KEY=<generate-a-random-jwt-secret>
RATE_LIMIT=60/minute
CORS_ORIGINS=https://your-frontend-url.vercel.app
LOG_LEVEL=INFO
```

**Important**: After deployment, update `CORS_ORIGINS` with your actual Vercel frontend URL.

## Post-Deployment

1. Your API will be available at: `https://vysalytica-api.onrender.com`
2. Test the health endpoint: `https://vysalytica-api.onrender.com/healthz`
3. Copy this URL - you'll need it for the frontend deployment

## Notes

- Free tier may spin down after inactivity (cold starts ~30 seconds)
- SQLite database will reset on each deployment (consider upgrading to PostgreSQL for production)
- Logs are available in the Render dashboard
