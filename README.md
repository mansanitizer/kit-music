# YouTube Audio Proxy for Railway

FastAPI service that streams YouTube audio using yt-dlp. Deployed on Railway to bypass Lambda Python limitations.

## Local Development

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run locally
```bash
uvicorn main:app --reload
```

The service will be available at `http://localhost:8000`.

### Test endpoints

**Health check:**
```bash
curl http://localhost:8000/health
```

**Stream audio:**
```bash
curl -I http://localhost:8000/stream/dQw4w9WgXcQ
```

## Deploy to Railway

### Option 1: Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project in this directory
cd youtube-proxy
railway init

# Deploy
railway up
```

### Option 2: Railway Dashboard

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Set the root directory to `youtube-proxy`
5. Railway will auto-detect Python and deploy

### Get your Railway URL

After deployment, Railway will provide a URL like:
```
https://your-service.railway.app
```

Copy this URL - you'll need to add it to Netlify as `RAILWAY_PROXY_URL`.

## Environment Variables

Railway automatically sets `PORT=8000`. No additional environment variables are required for basic operation.

### Optional environment variables:
- `PROXY_URL` - HTTP proxy for YouTube requests (e.g., residential proxy)
- `PYTHON_VERSION` - Python version (default: 3.11)

## Endpoints

### `GET /`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "youtube-audio-proxy"
}
```

### `GET /health`
Detailed health check with version information.

**Response:**
```json
{
  "status": "healthy",
  "yt_dlp_version": "2024.12.13",
  "service": "youtube-audio-proxy"
}
```

### `GET /stream/{video_id}`
Stream audio for a YouTube video.

**Parameters:**
- `video_id` - YouTube video ID (e.g., `dQw4w9WgXcQ`)

**Response:**
- Streams audio as `audio/mpeg`
- Headers include `Content-Disposition` with filename

**Example:**
```bash
curl https://your-service.railway.app/stream/dQw4w9WgXcQ -o audio.mp3
```

## Integration with Netlify

After deploying to Railway:

1. Go to your Netlify site → **Site configuration** → **Environment variables**
2. Add:
   - Key: `RAILWAY_PROXY_URL`
   - Value: `https://your-service.railway.app` (your actual Railway URL)
3. Redeploy your Netlify site

The Netlify function at `/api/music/stream` will proxy requests through Railway.

## Monitoring

### View Railway logs

**Via CLI:**
```bash
railway logs
```

**Via Dashboard:**
1. Go to Railway dashboard
2. Select your service
3. Click **Deployments** → **View Logs**

## Troubleshooting

### "Video not found" errors
- Video might be age-restricted, private, or deleted
- Try a different video ID

### "Failed to fetch stream: 403" errors
- YouTube may be blocking Railway IPs
- Consider adding cookies or using a residential proxy
- Update yt-dlp: `pip install -U yt-dlp`

### Service not responding
- Check Railway logs for errors
- Verify PORT is set correctly (Railway handles this automatically)
- Ensure service is running (not paused)

## Cost Estimate

**Railway Pricing:**
- Free tier: $5 credit/month
- Pro: $5/month + usage
- Bandwidth: ~$0.10/GB

**Typical usage:** ~10GB/month = ~$6-7/month total

## Anti-Detection Features

The service includes:
- Custom user agents
- YouTube referer headers
- Android & web player clients
- Skips DASH/HLS formats for better compatibility

See `main.py` for full yt-dlp configuration.
