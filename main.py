from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import asyncio
import logging
from typing import AsyncIterator
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Audio Proxy")

# CORS - allow Netlify domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your Netlify domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# yt-dlp options with aggressive anti-detection
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'referer': 'https://www.youtube.com/',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-us,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    },
    # Anti-bot measures
    'extractor_args': {
        'youtube': {
            'skip': ['dash', 'hls'],
            'player_client': ['android', 'web'],
            'player_skip': ['webpage', 'configs'],
        }
    },
}

async def stream_audio(url: str) -> AsyncIterator[bytes]:
    """Stream audio chunks from YouTube URL"""
    try:
        # Get video info
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise HTTPException(status_code=404, detail="Video not found")
            
            # Get the best audio format URL
            formats = info.get('formats', [])
            audio_format = None
            
            # Prefer audio-only formats
            for fmt in formats:
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    audio_format = fmt
                    break
            
            # Fallback to any format with audio
            if not audio_format:
                for fmt in formats:
                    if fmt.get('acodec') != 'none':
                        audio_format = fmt
                        break
            
            if not audio_format or not audio_format.get('url'):
                raise HTTPException(status_code=404, detail="No playable audio format found")
            
            stream_url = audio_format['url']
            logger.info(f"Streaming from URL: {stream_url[:100]}...")
            
            # Stream the audio
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    stream_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Range': 'bytes=0-',  # Support range requests
                    }
                ) as resp:
                    if resp.status != 200 and resp.status != 206:
                        raise HTTPException(
                            status_code=resp.status,
                            detail=f"Failed to fetch stream: {resp.status}"
                        )
                    
                    # Stream in chunks
                    async for chunk in resp.content.iter_chunked(8192):
                        yield chunk
                        
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "youtube-audio-proxy"}

@app.get("/stream/{video_id}")
async def stream_video(video_id: str):
    """Stream audio for a YouTube video ID"""
    try:
        logger.info(f"Stream request for video: {video_id}")
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        return StreamingResponse(
            stream_audio(url),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="track-{video_id}.mp3"',
                "Cache-Control": "no-cache",
                "Accept-Ranges": "bytes",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "yt_dlp_version": yt_dlp.version.__version__,
        "service": "youtube-audio-proxy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
