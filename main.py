from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import asyncio
import logging
from typing import AsyncIterator
import aiohttp
from aiohttp.client_exceptions import ClientPayloadError

import os
import json
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HARDCODED_COOKIES_JSON = '''[
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.791868,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__Secure-1PAPISID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g8fLy06O7817f4d7/ABHkZWPdhHhDBuM2E",
    "id": 1
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.79222,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-1PSID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g.a0005gihkaUJo5dyQuclklQzrGKtBKI8oEluGV0M86xSATX56OK3LFAMCy_g5w4jqYUruR6FIgACgYKAY4SARASFQHGX2MidpDYZ0fleISH4gs-IUgWNxoVAUF8yKroYt1pFag31sK0k5t93ZI50076",
    "id": 2
},
{
    "domain": ".youtube.com",
    "expirationDate": 1799692665.905651,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-1PSIDCC",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AKEyXzW9DrCQF5t2TcTChPuNjEHsmjSHWqad30xcH6iMDvfIfShUGqj4S4-NHwucJ_Flz1qrpA",
    "id": 3
},
{
    "domain": ".youtube.com",
    "expirationDate": 1799692665.751107,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-1PSIDTS",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "sidts-CjQB7I_69E_GoIAyZQTH5t6U8Ljj11_hJZl7vg4KRKDUiCOkLKAzi9KPjgaz7UAbdxr2-wJgEAA",
    "id": 4
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.791905,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__Secure-3PAPISID",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g8fLy06O7817f4d7/ABHkZWPdhHhDBuM2E",
    "id": 5
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.792271,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-3PSID",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g.a0005gihkaUJo5dyQuclklQzrGKtBKI8oEluGV0M86xSATX56OK3eZfahOGsiEkjn9H4b8sC5wACgYKAXMSARASFQHGX2MiOkRDDpW8e2sFRo8HBKIV2xoVAUF8yKqdLJUFRs9rko2TT0NebLe90076",
    "id": 6
},
{
    "domain": ".youtube.com",
    "expirationDate": 1799692665.905799,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-3PSIDCC",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AKEyXzXOzHWheZkH4fxaVVQe7LqFxFOU2laHFHcG5myxpWtXy_EjUUA-rEPvfEFiah812jEV2A",
    "id": 7
},
{
    "domain": ".youtube.com",
    "expirationDate": 1799692665.753681,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-3PSIDTS",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "sidts-CjQB7I_69E_GoIAyZQTH5t6U8Ljj11_hJZl7vg4KRKDUiCOkLKAzi9KPjgaz7UAbdxr2-wJgEAA",
    "id": 8
},
{
    "domain": ".youtube.com",
    "expirationDate": 1775056888,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_gcl_au",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "1.1.1124808925.1767280888",
    "id": 9
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.791798,
    "hostOnly": false,
    "httpOnly": false,
    "name": "APISID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "MubTzyJ2vS7TmZsd/At-qJt6WZWVQg8aVd",
    "id": 10
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.791648,
    "hostOnly": false,
    "httpOnly": true,
    "name": "HSID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "AJ-DtCRFRt8K37Xic",
    "id": 11
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714933.434108,
    "hostOnly": false,
    "httpOnly": true,
    "name": "LOGIN_INFO",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AFmmF2swRAIgGYKqjEpflE_momHako0Dyff3b5YgmcnHEEqIqDzyhAsCIEmB55J6vNtVMk0vNENvtUlKabpjdoCeFJohLzbDONyh:QUQ3MjNmeW1WZW45VVhaT3FhVmlMU1FfTHZoYWtxcm5ueXhRQ2l2X1RoRmFMa21wMkpBTmNBTzFKeFp1eVZlajVVbE93ZWh3cmdXTlEyQUNKTFVNNEs4MUlDbFdjYzZfdWhZcTRwcU1yekNwZHQ3UHlRMDZ1dXlsQnlVQ1BzOGg2MmJIYXM0UWVTbVlMMmI5NGZOWnM0anZOVVlrRTRRY0N3",
    "id": 12
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802715075.928989,
    "hostOnly": false,
    "httpOnly": false,
    "name": "PREF",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "f6=40000000&f7=100&tz=Asia.Calcutta&repeat=NONE&f4=4000000&f5=30000",
    "id": 13
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.791832,
    "hostOnly": false,
    "httpOnly": false,
    "name": "SAPISID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g8fLy06O7817f4d7/ABHkZWPdhHhDBuM2E",
    "id": 14
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.792142,
    "hostOnly": false,
    "httpOnly": false,
    "name": "SID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "g.a0005gihkaUJo5dyQuclklQzrGKtBKI8oEluGV0M86xSATX56OK3npoU3OLO0QBenuslLuEOmAACgYKAfkSARASFQHGX2Mi_CbHVo_HKMPudT7rNN3a-RoVAUF8yKoNxPop8qXKKa_Sd0AiWVXe0076",
    "id": 15
},
{
    "domain": ".youtube.com",
    "expirationDate": 1799692665.90547,
    "hostOnly": false,
    "httpOnly": false,
    "name": "SIDCC",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "AKEyXzW3bo4L2nm18QZLHjJzQ92fFz1uvfvxjQjr8X0DmvsJU4FkDWaQRzAHrTpNX8gFZ3I0jw",
    "id": 16
},
{
    "domain": ".youtube.com",
    "expirationDate": 1802714924.79176,
    "hostOnly": false,
    "httpOnly": true,
    "name": "SSID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "A350PAE68UeXO0U1f",
    "id": 17
}
]'''

def setup_cookies():
    """Setup cookies from hardcoded JSON or environment variable, converting to Netscape format"""
    # Prioritize hardcoded cookies as requested for debugging
    cookies_env = HARDCODED_COOKIES_JSON
    
    if not cookies_env:
        cookies_env = os.environ.get('YOUTUBE_COOKIES')
        
    if not cookies_env:
        logger.error("MISSING: YOUTUBE_COOKIES environment variable and HARDCODED_COOKIES_JSON are not set!")
        # Log all keys to help debug
        keys = list(os.environ.keys())
        # Mask sensitive keys
        safe_keys = [k for k in keys if not any(s in k.lower() for s in ['key', 'secret', 'token', 'pass'])]
        logger.info(f"Available environment variables (keys only): {', '.join(safe_keys)}")
        return None
        
    try:
        cookies = json.loads(cookies_env)
        
        # Create a temp file for cookies
        fd, path = tempfile.mkstemp(suffix='.txt', text=True)
        
        with os.fdopen(fd, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This file was generated by youtube-proxy\n\n")
            
            for cookie in cookies:
                domain = cookie.get('domain', '')
                if not domain: continue
                
                # Netscape spec: domain, include_subdomains, path, secure, expiry, name, value
                if domain == 'youtube.com' or domain == '.youtube.com':
                    # Force subdomain inclusion for main domain cookies to ensure they work on www.youtube.com
                    domain = '.youtube.com'
                    include_subdomains = "TRUE"
                else:
                    include_subdomains = "TRUE" if domain.startswith('.') else "FALSE"
                
                cookie_path = cookie.get('path', '/')
                secure = "TRUE" if cookie.get('secure', False) else "FALSE"
                
                # Expiry: safe handling of missing or null expirationDate
                expiry = 0
                if 'expirationDate' in cookie and cookie['expirationDate'] is not None:
                    expiry = int(cookie['expirationDate'])
                
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                f.write(f"{domain}\t{include_subdomains}\t{cookie_path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        
        logger.info(f"Created Netscape format cookie file at {path}")
        return path
    except Exception as e:
        logger.error(f"Failed to setup cookies: {e}")
        return None

COOKIE_FILE = setup_cookies()

app = FastAPI(title="YouTube Audio Proxy")

# CORS - allow Netlify domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your Netlify domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# yt-dlp options (simplified for reliability with specific cookies)
# yt-dlp options (simplified for reliability with specific cookies)
# yt-dlp options (simplified for reliability with specific cookies)
YDL_OPTS_AUDIO = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
}

if COOKIE_FILE:
    YDL_OPTS_AUDIO['cookiefile'] = COOKIE_FILE


# yt-dlp options for video - Capped at 480p for retro aesthetic
YDL_OPTS_VIDEO = {
    'format': 'best[height<=480]/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
}

if COOKIE_FILE:
    YDL_OPTS_VIDEO['cookiefile'] = COOKIE_FILE


async def stream_content(url: str, is_video: bool = False, client_headers: dict = None) -> AsyncIterator[bytes]:
    """Stream audio or video chunks from YouTube URL"""
    try:
        opts = YDL_OPTS_VIDEO if is_video else YDL_OPTS_AUDIO
        
        # Get video info
        with yt_dlp.YoutubeDL(opts) as ydl:
            logger.info(f"Extracting info for {url} (video={is_video})")
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error(f"yt-dlp failed to extract info for {url}")
                raise HTTPException(status_code=404, detail="Video not found")
            
            stream_url = info.get('url')
            
            if not stream_url:
                formats = info.get('formats', [])
                selected_format = None
                
                if not is_video:
                    for fmt in formats:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            selected_format = fmt
                            break
                
                if not selected_format:
                    for fmt in formats:
                        if fmt.get('url'):
                            if is_video:
                                if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                                    selected_format = fmt
                                    break
                            else:
                                if fmt.get('acodec') != 'none':
                                    selected_format = fmt
                                    break
                
                if not selected_format and formats:
                    selected_format = formats[0]
                
                if not selected_format or not selected_format.get('url'):
                    raise HTTPException(status_code=404, detail="No playable format found")
                
                stream_url = selected_format['url']
            
            logger.info(f"Streaming {'video' if is_video else 'audio'} from URL: {stream_url[:100]}...")
            
            # Stream with comprehensive headers
            timeout = aiohttp.ClientTimeout(total=600 if is_video else 60, connect=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
            # Prepare headers for the final YouTube fetch
                target_headers = selected_format.get('http_headers', {}).copy()
                if not target_headers:
                    target_headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                        'Accept': '*/*', 
                    }
                
                # Pass through the Range header if requested by the client
                if client_headers and 'range' in {k.lower() for k in client_headers}:
                    range_val = next(v for k, v in client_headers.items() if k.lower() == 'range')
                    target_headers['Range'] = range_val
                    logger.info(f"Forwarding client range: {range_val}")
                else:
                    target_headers['Range'] = 'bytes=0-'
                
                async with session.get(
                    stream_url,
                    headers=target_headers,
                    allow_redirects=True
                ) as resp:
                    if resp.status not in [200, 206]:
                        err_text = await resp.text()
                        logger.error(f"YouTube fetch failed: {resp.status} - {err_text[:200]}")
                        raise HTTPException(
                            status_code=resp.status,
                            detail=f"Failed to fetch from YouTube: {resp.status}"
                        )
                    
                    logger.info(f"YouTube responded with {resp.status}, content-length: {resp.headers.get('Content-Length')}")
                    
                    chunk_size = 65536 if is_video else 16384
                    count = 0
                    try:
                        async for chunk in resp.content.iter_chunked(chunk_size):
                            yield chunk
                            count += 1
                            if count == 1:
                                logger.info("First chunk yielded successfully")
                    except ClientPayloadError as e:
                        logger.warning(f"Stream interrupted (ClientPayloadError): {e}")
                        # Don't re-raise, just stop yielding
                        return
                    except Exception as e:
                        logger.error(f"Stream error during iteration: {e}")
                        raise e
                    
                    if count == 0:
                        logger.warning("No chunks were yielded from YouTube response body!")
                        
    except Exception as e:
        logger.error(f"Stream error: {str(e)}", exc_info=True)
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=str(e))
        raise e

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "youtube-proxy"}

@app.api_route("/stream/{video_id}", methods=["GET", "HEAD"])
async def stream_audio(video_id: str, request: Request):
    """Stream audio for a YouTube video ID"""
    try:
        logger.info(f"Audio {request.method} request for: {video_id}")
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        if request.method == "HEAD":
            return Response(status_code=200, headers={"Accept-Ranges": "bytes", "Content-Type": "audio/mpeg"})

        return StreamingResponse(
            stream_content(url, is_video=False, client_headers=dict(request.headers)),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="audio-{video_id}.mp3"',
                "Cache-Control": "no-cache",
                "Accept-Ranges": "bytes",
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in stream_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/video/{video_id}", methods=["GET", "HEAD"])
async def stream_video(video_id: str, request: Request):
    """Stream video for a YouTube video ID"""
    try:
        logger.info(f"Video {request.method} request for: {video_id}")
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        if request.method == "HEAD":
            return Response(status_code=200, headers={"Accept-Ranges": "bytes", "Content-Type": "video/mp4"})

        return StreamingResponse(
            stream_content(url, is_video=True, client_headers=dict(request.headers)),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'inline; filename="video-{video_id}.mp4"',
                "Cache-Control": "no-cache",
                "Accept-Ranges": "bytes",
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in stream_video: {str(e)}")
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

