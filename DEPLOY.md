# 🚀 Deployment Guide - Streamlit Cloud

## Deploying to Streamlit Cloud

### Step 1: Prepare Your Repository

1. Make sure your code is pushed to GitHub
2. Ensure `streamlit_app.py` exists in the root directory (already created)

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `people-counter-system`
5. **Main file path**: `streamlit_app.py`
6. **Branch**: `main` (or your default branch)
7. Click "Deploy"

### Step 3: Configure Environment Variables (Optional)

If your backend API is hosted separately, add environment variables:

1. Go to your app settings on Streamlit Cloud
2. Click "Secrets" or "Environment variables"
3. Add:
   ```
   API_BASE_URL=https://your-backend-api-url.com
   API_PORT=8000
   ```

### Step 4: Backend Deployment

The backend API needs to be deployed separately. Options:

#### Option A: Deploy Backend on Railway/Render/Fly.io

1. Create a new service
2. Set the start command: `python run_backend.py`
3. Get the URL (e.g., `https://your-api.railway.app`)
4. Set `API_BASE_URL` in Streamlit Cloud to this URL

#### Option B: Use Local Backend (Development Only)

For local development, run backend separately:
```bash
python run_backend.py
```

## File Structure for Cloud

```
people-counter-system/
├── streamlit_app.py      # Entry point for Streamlit Cloud
├── frontend/
│   └── app.py           # Main Streamlit app
├── backend/
│   └── api.py           # FastAPI backend
├── requirements.txt     # Dependencies
└── .streamlit/
    └── config.toml      # Streamlit config
```

## Troubleshooting

### App Not Starting

- Check that `streamlit_app.py` exists in root
- Verify `frontend/app.py` is accessible
- Check logs in Streamlit Cloud dashboard

### API Connection Issues

- Verify `API_BASE_URL` is set correctly
- Check backend is running and accessible
- Test API endpoint: `curl https://your-api-url.com/`

### Import Errors

- Ensure all dependencies are in `requirements.txt`
- Check Python version compatibility (3.8+)

## Notes

- Streamlit Cloud has resource limits
- Large video processing may timeout
- Consider using background jobs for long-running tasks
- Backend should be deployed separately for production use

