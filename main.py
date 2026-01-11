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

# yt-dlp options optimized for Android Music client (reliable without PO tokens)
YDL_OPTS_AUDIO = {
    'format': 'bestaudio*',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'user_agent': 'com.google.android.apps.youtube.music/6.42.52 (Linux; U; Android 13; en_US)',
    'referer': 'https://www.youtube.com/',
    'http_headers': {
        'User-Agent': 'com.google.android.apps.youtube.music/6.42.52 (Linux; U; Android 13; en_US)',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'X-YouTube-Client-Name': '3',
        'X-YouTube-Client-Version': '18.11.34',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android_music', 'android'],
            'player_skip': ['webpage'],
        }
    },
}

# yt-dlp options for video - Capped at 480p for retro aesthetic and bandwidth efficiency
YDL_OPTS_VIDEO = {
    'format': 'best[height<=480][ext=mp4]/best[height<=480]/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'referer': 'https://www.youtube.com/',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    },
}

async def stream_content(url: str, is_video: bool = False) -> AsyncIterator[bytes]:
    """Stream audio or video chunks from YouTube URL"""
    try:
        opts = YDL_OPTS_VIDEO if is_video else YDL_OPTS_AUDIO
        
        # Get video info
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise HTTPException(status_code=404, detail="Video not found")
            
            # Try to get stream URL
            stream_url = info.get('url')
            
            if not stream_url:
                formats = info.get('formats', [])
                selected_format = None
                
                if not is_video:
                    # Prefer audio-only formats
                    for fmt in formats:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            selected_format = fmt
                            break
                
                # Fallback or video selection
                if not selected_format:
                    for fmt in formats:
                        if fmt.get('url'):
                            # For video, we want both audio and video
                            if is_video:
                                if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                    selected_format = fmt
                                    break
                            else:
                                if fmt.get('acodec') != 'none':
                                    selected_format = fmt
                                    break
                
                # Final resort
                if not selected_format and formats:
                    selected_format = formats[0]
                
                if not selected_format or not selected_format.get('url'):
                    raise HTTPException(status_code=404, detail="No playable format found")
                
                stream_url = selected_format['url']
            
            logger.info(f"Streaming {'video' if is_video else 'audio'} from URL: {stream_url[:100]}...")
            
            # Stream with comprehensive headers
            timeout = aiohttp.ClientTimeout(total=300 if is_video else 30, connect=10) # Larger timeout for video
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = opts['http_headers'].copy()
                headers['Range'] = 'bytes=0-'
                
                async with session.get(
                    stream_url,
                    headers=headers,
                    allow_redirects=True
                ) as resp:
                    if resp.status not in [200, 206]:
                        logger.error(f"Stream fetch failed: {resp.status} - {await resp.text()}")
                        raise HTTPException(
                            status_code=resp.status,
                            detail=f"Failed to fetch stream: {resp.status}"
                        )
                    
                    # Stream in larger chunks for video
                    chunk_size = 65536 if is_video else 8192
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        yield chunk
                        
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "youtube-proxy"}

@app.get("/stream/{video_id}")
async def stream_audio(video_id: str):
    """Stream audio for a YouTube video ID"""
    try:
        logger.info(f"Audio stream request for video: {video_id}")
        url = f"https://www.youtube.com/watch?v={video_id}"
        return StreamingResponse(
            stream_content(url, is_video=False),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="audio-{video_id}.mp3"',
                "Cache-Control": "no-cache",
                "Accept-Ranges": "bytes",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming audio {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/{video_id}")
async def stream_video(video_id: str):
    """Stream video for a YouTube video ID"""
    try:
        logger.info(f"Video stream request for video: {video_id}")
        url = f"https://www.youtube.com/watch?v={video_id}"
        return StreamingResponse(
            stream_content(url, is_video=True),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'inline; filename="video-{video_id}.mp4"',
                "Cache-Control": "no-cache",
                "Accept-Ranges": "bytes",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "yt_dlp_version": yt_dlp.version.__version__,
        "service": "youtube-proxy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

