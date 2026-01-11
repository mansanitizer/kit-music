from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
import yt_dlp
import asyncio
import logging
from typing import AsyncIterator
import aiohttp
from aiohttp.client_exceptions import ClientPayloadError
import subprocess
import os
import json
import tempfile
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global OAuth State
class AuthState:
    def __init__(self):
        self.current_code = None
        self.current_url = None
        self.is_linking = False
        self.last_error = None
        self.auth_file = '/tmp/yt-auth.json'
        self.manual_cookie_file = '/tmp/manual_cookies.txt'
        self.manual_ua_file = '/tmp/manual_ua.txt'
        self.cache_dir = '/tmp/yt-cache'

    def get_manual_ua(self):
        """Read saved User-Agent"""
        if os.path.exists(self.manual_ua_file):
            try:
                with open(self.manual_ua_file, 'r') as f:
                    return f.read().strip()
            except: pass
        return None

    def get_cookies_for_aiohttp(self):
        """Parse Netscape/JSON cookies for aiohttp"""
        cookies = {}
        target = self.manual_cookie_file
        if not os.path.exists(target):
            return cookies
            
        try:
            with open(target, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return cookies
                if content.startswith('['):
                    import json
                    data = json.loads(content)
                    for c in data:
                        cookies[c['name']] = c['value']
                else:
                    for line in content.splitlines():
                        if not line.startswith('#') and '\t' in line:
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookies[parts[5]] = parts[6].strip()
        except Exception as e:
            logger.error(f"Error parsing cookies for aiohttp: {e}")
        return cookies

auth_state = AuthState()

app = FastAPI(title="YouTube Audio Proxy")

# CORS - allow Netlify domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your Netlify domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/update-cookies")
async def update_cookies(request: Request):
    """Receive and save cookies and UA from the dashboard"""
    try:
        data = await request.json()
        cookies = data.get('cookies', '').strip()
        ua = data.get('ua', '').strip()
        
        # Save cookies
        with open(auth_state.manual_cookie_file, 'w') as f:
            f.write(cookies)
        
        # Save User-Agent
        if ua:
            with open(auth_state.manual_ua_file, 'w') as f:
                f.write(ua)
        elif os.path.exists(auth_state.manual_ua_file):
            os.remove(auth_state.manual_ua_file)
            
        logger.info(f"Manual cookies updated (UA provided: {bool(ua)})")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating cookies: {e}")
        raise HTTPException(status_code=400, detail=str(e))

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


YDL_OPTS_AUDIO = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'android']}},
    'cache_dir': '/tmp/yt-cache'
}

YDL_OPTS_VIDEO = {
    'format': 'best[height<=480]/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'android']}},
    'cache_dir': '/tmp/yt-cache'
}

# Check for OAuth - this is more reliable for bot detection
# yt-dlp stores oauth tokens in the cache dir
if os.path.exists('/tmp/yt-cache'):
    YDL_OPTS_AUDIO['username'] = 'oauth2'
    YDL_OPTS_VIDEO['username'] = 'oauth2'
    logger.info("Found OAuth cache, enabling OAuth2 for extraction")

if COOKIE_FILE:
    YDL_OPTS_AUDIO['cookiefile'] = COOKIE_FILE
    YDL_OPTS_VIDEO['cookiefile'] = COOKIE_FILE


async def stream_content(url: str, is_video: bool = False, client_headers: dict = None) -> AsyncIterator[bytes]:
    """Stream audio or video chunks from YouTube URL"""
    try:
        # Get video info
        opts = YDL_OPTS_VIDEO.copy() if is_video else YDL_OPTS_AUDIO.copy()
        
        if os.path.exists(auth_state.manual_cookie_file):
            logger.info("Using manual cookies for extraction")
            opts['cookiefile'] = auth_state.manual_cookie_file
        elif os.path.exists('/tmp/yt-cache'):
            opts['username'] = 'oauth2'
            logger.info("Using OAuth2 for extraction")
        
        manual_ua = auth_state.get_manual_ua()
        if manual_ua:
            opts['user_agent'] = manual_ua
            logger.info("Using manual User-Agent for extraction")
            
        try:
             with yt_dlp.YoutubeDL(opts) as ydl:
                logger.info(f"Extracting info for {url} (video={is_video})")
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            # Fallback chain: Try different clients/cookie combinations
            error_msg = str(e).lower()
            logger.warning(f"Primary strategy failed ({e})")
            
            # The order of fallback is crucial: 
            # 1. TV with cookies (most lenient for authenticated)
            # 2. WEB with cookies (most flexible for formats)
            # 3. IOS with cookies
            # 4. TV WITHOUT cookies (bypass IP-based cookie tainting)
            # 5. IOS WITHOUT cookies
            fallback_strategies = [
                ({'youtube': {'player_client': ['tv']}}, True),
                ({'youtube': {'player_client': ['web']}}, True),
                ({'youtube': {'player_client': ['ios']}}, True),
                ({'youtube': {'player_client': ['tv']}}, False),
                ({'youtube': {'player_client': ['ios']}}, False),
                ({'youtube': {'player_client': ['mweb']}}, False),
            ]
            
            info = None
            last_err = e
            for strategy_args, use_cookies in fallback_strategies:
                f_opts = opts.copy()
                if not use_cookies and 'cookiefile' in f_opts:
                    del f_opts['cookiefile']
                elif use_cookies and not f_opts.get('cookiefile'):
                    if os.path.exists(auth_state.manual_cookie_file):
                        f_opts['cookiefile'] = auth_state.manual_cookie_file
                    elif COOKIE_FILE:
                        f_opts['cookiefile'] = COOKIE_FILE
                
                if manual_ua:
                    f_opts['user_agent'] = manual_ua
                
                f_opts['extractor_args'] = strategy_args
                
                try:
                    with yt_dlp.YoutubeDL(f_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            logger.info(f"Success with strategy: {strategy_args}")
                            break
                except Exception as fe:
                    logger.warning(f"Strategy {strategy_args} failed: {fe}")
                    last_err = fe
            
            if not info:
                raise last_err
            
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
        else:
            selected_format = info
        
        logger.info(f"Streaming {'video' if is_video else 'audio'} from URL: {stream_url[:100]}...")
        
        # Stream with comprehensive headers
        timeout = aiohttp.ClientTimeout(total=1200 if is_video else 300, connect=30)
        cookies = auth_state.get_cookies_for_aiohttp()
        manual_ua = auth_state.get_manual_ua()
        
        async with aiohttp.ClientSession(timeout=timeout, cookies=cookies) as session:
            # Prepare headers for the final YouTube fetch
            target_headers = selected_format.get('http_headers', {}).copy()
            
            # Use manual UA if available, otherwise ensure a modern UA
            ua = manual_ua or target_headers.get('User-Agent', '')
            if not ua or 'Googlebot' in ua or 'python' in ua.lower():
                 target_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
            else:
                 target_headers['User-Agent'] = ua
            
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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Win98 Style Management Dashboard"""
    
    # Check if we have auth or cookies
    has_cookies = COOKIE_FILE is not None
    has_oauth = os.path.exists(auth_state.auth_file)
    has_manual = os.path.exists(auth_state.manual_cookie_file)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Proxy - Control Panel</title>
        <link rel="stylesheet" href="https://unpkg.com/98.css">
        <style>
            body {{ background-color: #008080; padding: 20px; font-family: "MS Sans Serif", Arial, sans-serif; }}
            .window {{ max-width: 600px; margin: 0 auto; }}
            .status-bar {{ padding: 2px; }}
            .auth-box {{ margin-top: 10px; padding: 10px; background: #fff; border: 1px inset #808080; min-height: 50px; }}
            pre {{ font-family: monospace; font-size: 12px; }}
            .btn-large {{ margin: 5px; }}
            .hidden {{ display: none; }}
            .code-text {{ font-size: 24px; font-weight: bold; color: blue; text-align: center; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="window">
            <div class="title-bar">
                <div class="title-bar-text">YouTube Proxy Configuration</div>
                <div class="title-bar-controls">
                    <button aria-label="Minimize"></button>
                    <button aria-label="Maximize"></button>
                    <button aria-label="Close"></button>
                </div>
            </div>
            <div class="window-body">
                <p>Status: <strong>Proxy is Online</strong></p>
                
                <fieldset>
                    <legend>Authentication Methods</legend>
                    <div class="field-row">
                        <label>Manual Cookies:</label>
                        <span>{ "ACTIVE (Recent Sync)" if has_manual else "NONE" }</span>
                    </div>
                    <div class="field-row">
                        <label>Hardcoded Cookies:</label>
                        <span>{ "FALLBACK ACTIVE" if has_cookies else "INACTIVE" }</span>
                    </div>
                    <div class="field-row">
                        <label>YouTube Account (OAuth2):</label>
                        <span>{ "LINKED" if has_oauth else "NOT LINKED" }</span>
                    </div>
                </fieldset>

                <div style="margin-top: 20px; display: flex; flex-wrap: wrap; justify-content: center;">
                    <button onclick="showCookieDialog()" class="btn-large">Sync Cookies manually...</button>
                    <button onclick="clearCookies()" class="btn-large" style="color: darkred;">Clear Saved Cookies</button>
                    <button onclick="window.location.reload()" class="btn-large">Refresh Status</button>
                </div>

                <div id="cookieDialog" class="hidden">
                    <fieldset style="margin-top: 20px;">
                        <legend>Cookie Sync</legend>
                        <p>1. Paste your <strong>User-Agent</strong> from your browser:</p>
                        <input id="uaInput" type="text" style="width: 100%; margin-bottom: 10px;" placeholder="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...">
                        
                        <p>2. Paste your <strong>YouTube Cookies</strong> (Netscape or JSON):</p>
                        <textarea id="cookieInput" style="width: 100%; height: 100px; margin-bottom: 10px;" placeholder="# Netscape HTTP Cookie File... or [{...}]"></textarea>
                        
                        <button onclick="saveCookies()">Save & Sync</button>
                        <button onclick="hideCookieDialog()">Cancel</button>
                    </fieldset>
                </div>

                <div id="authDialog" class="hidden">
                    <fieldset style="margin-top: 20px;">
                        <legend>Linking Instructions</legend>
                        <p id="authMsg">Please wait, generating link code...</p>
                        <div id="authCodeBox" class="hidden">
                            <p>1. Go to: <a href="#" id="authUrl" target="_blank">Loading...</a></p>
                            <p>2. Enter this code:</p>
                            <div class="code-text" id="authCode">---- ----</div>
                            <p>3. Complete the login on your phone/browser.</p>
                            <p><i>Note: OAuth linking is currently unstable on some IPs.</i></p>
                        </div>
                    </fieldset>
                </div>
                
                <fieldset style="margin-top: 20px;">
                    <legend>Test Streaming</legend>
                    <div class="field-row">
                        <label for="testVideoId">YouTube Video ID:</label>
                        <input id="testVideoId" type="text" value="pEl3-0GHyoQ" style="width: 100px;">
                    </div>
                    <div style="margin-top: 10px;">
                        <button onclick="runTest('audio')">Test Audio Stream</button>
                        <button onclick="runTest('video')">Test Video Stream</button>
                    </div>
                    <div id="testStatus" class="auth-box hidden" style="margin-top: 10px; font-size: 11px;">
                        <strong>Test Results:</strong>
                        <ul id="testSteps" style="margin-top: 5px; padding-left: 20px;"></ul>
                    </div>
                </fieldset>

                <fieldset style="margin-top: 20px;">
                    <legend>Troubleshooting</legend>
                    <p>1. Install the "Get cookies.txt LOCALLY" extension in Chrome/Edge.</p>
                    <p>2. Export cookies for youtube.com and paste them into "Sync Cookies" above.</p>
                </fieldset>
            </div>
            <div class="status-bar">
                <p class="status-bar-field">v{yt_dlp.version.__version__}</p>
                <p class="status-bar-field">CPU: {psutil.cpu_percent()}%</p>
                <p class="status-bar-field">System: Python 3.11</p>
            </div>
        </div>

        <script>
            async function startLinking() {{
                const btn = document.getElementById('linkBtn');
                const dialog = document.getElementById('authDialog');
                const msg = document.getElementById('authMsg');
                const codeBox = document.getElementById('authCodeBox');
                
                btn.disabled = true;
                dialog.classList.remove('hidden');
                document.getElementById('cookieDialog').classList.add('hidden');
                
                try {{
                    const resp = await fetch('/auth/link');
                    const data = await resp.json();
                    
                    if (data.status === 'linking' || data.status === 'started') {{
                         pollStatus();
                    }} else {{
                        alert('Error: ' + data.detail);
                        btn.disabled = false;
                    }}
                }} catch (e) {{
                    alert('Network error: ' + e);
                    btn.disabled = false;
                }}
            }}
            function showCookieDialog() {{
                document.getElementById('cookieDialog').classList.remove('hidden');
                document.getElementById('authDialog').classList.add('hidden');
            }}
            function hideCookieDialog() {{
                document.getElementById('cookieDialog').classList.add('hidden');
            }}

            async function clearCookies() {{
                if (!confirm('This will delete your manually synced cookies. Continue?')) return;
                try {{
                    const resp = await fetch('/auth/update-cookies', {{
                        method: 'POST',
                        body: ''
                    }});
                    const data = await resp.json();
                    alert('Cookies cleared. Redirecting...');
                    window.location.reload();
                }} catch (e) {{ alert('Error: ' + e); }}
            }}

            async function saveCookies() {{
                const cookies = document.getElementById('cookieInput').value;
                const ua = document.getElementById('uaInput').value;
                if (!cookies.trim()) return alert('Paste some cookies first!');
                
                try {{
                    const resp = await fetch('/auth/update-cookies', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ cookies, ua }})
                    }});
                    const data = await resp.json();
                    if (data.status === 'success') {{
                        alert('Auth updated! Stream tests recommended.');
                        window.location.reload();
                    }} else {{
                        alert('Error: ' + data.detail);
                    }}
                }} catch (e) {{
                    alert('Network error: ' + e);
                }}
            }}
            
            async function pollStatus() {{
                const msg = document.getElementById('authMsg');
                const codeBox = document.getElementById('authCodeBox');
                const codeLabel = document.getElementById('authCode');
                const urlLabel = document.getElementById('authUrl');
                
                const timer = setInterval(async () => {{
                    try {{
                        const resp = await fetch('/auth/status');
                        const data = await resp.json();
                        
                        if (data.code) {{
                            msg.innerText = 'Go to the URL below:';
                            codeBox.classList.remove('hidden');
                            codeLabel.innerText = data.code;
                            urlLabel.href = data.url;
                            urlLabel.innerText = data.url;
                        }}
                        
                        if (data.status === 'linked') {{
                            clearInterval(timer);
                            alert('YouTube account linked successfully!');
                            window.location.reload();
                        }}
                        
                        if (data.error) {{
                             clearInterval(timer);
                             alert('Linking failed: ' + data.error);
                             window.location.reload();
                         }}
                    }} catch (e) {{}}
                }}, 2000);
            }}

            async function runTest(type) {{
                const id = document.getElementById('testVideoId').value;
                const statusBox = document.getElementById('testStatus');
                const stepsList = document.getElementById('testSteps');
                
                if (!id) return alert('Enter a video ID!');
                
                statusBox.classList.remove('hidden');
                stepsList.innerHTML = '<li>Running ' + type + ' test...</li>';
                
                try {{
                    const resp = await fetch('/test/' + type + '/' + id);
                    const data = await resp.json();
                    
                    stepsList.innerHTML = '';
                    
                    if (data.auth_method) {{
                        const li = document.createElement('li');
                        li.innerHTML = '<strong>Auth Method:</strong> ' + data.auth_method;
                        stepsList.appendChild(li);
                    }}
                    
                    data.steps.forEach(step => {{
                        const li = document.createElement('li');
                        let icon = step.status === 'success' ? '✅' : (step.status === 'failed' ? '❌' : '⏳');
                        li.innerHTML = icon + ' ' + step.name + (step.error ? ': <span style="color:red">' + step.error + '</span>' : '');
                        if (step.title) li.innerHTML += ' (' + step.title + ')';
                        stepsList.appendChild(li);
                    }});
                    
                    if (data.success) {{
                        const li = document.createElement('li');
                        li.style.color = 'green';
                        li.style.fontWeight = 'bold';
                        li.style.marginTop = '5px';
                        li.innerText = 'OVERALL SUCCESS: Stream is reachable with current cookies!';
                        stepsList.appendChild(li);
                    }}
                }} catch (e) {{
                    stepsList.innerHTML += '<li style="color:red">Test failed to run: ' + e + '</li>';
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/auth/status")
async def get_auth_status():
    """Check current linking status"""
    status = "idle"
    if auth_state.is_linking:
        status = "linking"
    if os.path.exists(auth_state.auth_file):
        status = "linked"
        
    return {
        "status": status,
        "code": auth_state.current_code,
        "url": auth_state.current_url,
        "error": auth_state.last_error
    }

@app.get("/auth/link")
async def start_auth_link():
    """Trigger the yt-dlp OAuth flow in background"""
    if auth_state.is_linking:
        return {"status": "already_linking"}
        
    auth_state.is_linking = True
    auth_state.current_code = None
    auth_state.current_url = None
    auth_state.last_error = None
    
    # Start yt-dlp with --username oauth2 in a thread
    async def run_oauth():
        try:
            cmd = [
                "python3", "-m", "yt_dlp",
                "--username", "oauth2",
                "--password", "",
                "--cache-dir", "/tmp/yt-cache",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", # Neutral video
                "--simulate",
                "--no-check-certificate"
            ]
            
            logger.info(f"Starting OAuth process: {' '.join(cmd)}")
            
            # Using Popen to capture stdout/stderr
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_captured = []
            
            # Watch for the code in the output
            for line in process.stdout:
                line_str = line.strip()
                output_captured.append(line_str)
                logger.info(f"OAUTH: {line_str}")
                
                # [youtube] To sign in, go to https://www.google.com/device and enter ABCD-1234
                if "https://www.google.com/device" in line_str:
                    parts = line_str.split("enter")
                    if len(parts) > 1:
                        auth_state.current_code = parts[1].strip()
                        auth_state.current_url = "https://www.google.com/device"
                        logger.info(f"FOUND CODE: {auth_state.current_code}")
                
                if "logged in" in line_str.lower():
                    logger.info("OAuth success detected in logs")
                    
            process.wait()
            
            if process.returncode != 0 and not auth_state.current_code:
                 # Provide the last few lines of output for debugging
                 last_lines = "\\n".join(output_captured[-5:])
                 auth_state.last_error = f"Exit {process.returncode}: {last_lines}"
                 logger.error(f"OAuth failed with code {process.returncode}. Output: {last_lines}")
                 
            auth_state.is_linking = False
            
        except Exception as e:
            logger.error(f"OAuth thread failed: {e}")
            auth_state.last_error = str(e)
            auth_state.is_linking = False
            
    asyncio.create_task(run_oauth())
    return {"status": "started"}

@app.get("/")
async def root():
    """Home redirects to dashboard"""
    return RedirectResponse(url="/dashboard")

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

@app.get("/test/{test_type}/{video_id}")
async def test_stream(test_type: str, video_id: str):
    """Diagnose streaming issues and report detailed results to the dashboard"""
    is_video = test_type == "video"
    url = f"https://www.youtube.com/watch?v={video_id}"
    results = {
        "video_id": video_id,
        "type": test_type,
        "steps": [],
        "success": False
    }
    
    try:
        # Step 1: Info Extraction
        results["steps"].append({"name": "Extraction", "status": "pending"})
        opts = YDL_OPTS_VIDEO.copy() if is_video else YDL_OPTS_AUDIO.copy()
        
        auth_method = "None"
        manual_ua = auth_state.get_manual_ua()
        if manual_ua:
            opts['user_agent'] = manual_ua
            
        if os.path.exists(auth_state.manual_cookie_file):
            opts['cookiefile'] = auth_state.manual_cookie_file
            auth_method = "Manual Cookies"
        elif os.path.exists(auth_state.auth_file):
            opts['username'] = 'oauth2'
            auth_method = "OAuth2"
        elif COOKIE_FILE:
            opts['cookiefile'] = COOKIE_FILE
            auth_method = "Hardcoded Cookies"
            
        results["auth_method"] = auth_method
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                results["steps"][-1].update({"status": "success", "title": info.get('title')})
                
                # Capture all formats for debugging
                if info.get('formats'):
                    results["available_formats"] = [
                        {"ext": f.get('ext'), "resolution": f.get('resolution'), "note": f.get('format_note')}
                        for f in info['formats']
                    ][:20]  # Top 20
        except Exception as e:
            results["steps"][-1].update({"status": "failed", "error": str(e)})
            # If extraction failed, still try to see if a simple 'best' works
            results["steps"].append({"name": "Format Fallback Check", "status": "pending"})
            try:
                opts['format'] = 'best'
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    results["steps"][-1].update({"status": "success", "note": "Only generic 'best' format found"})
            except:
                results["steps"][-1].update({"status": "failed"})
                return results

        # Step 2: URL Resolution
        results["steps"].append({"name": "URL Resolution", "status": "pending"})
        stream_url = info.get('url')
        if not stream_url and info.get('formats'):
            # Fallback to finding a format
            formats = info.get('formats', [])
            for fmt in formats:
                if fmt.get('url'):
                    if not is_video and fmt.get('acodec') != 'none':
                        stream_url = fmt['url']
                        break
                    if is_video and fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                        stream_url = fmt['url']
                        break
            if not stream_url and formats:
                stream_url = formats[0]['url']
            
        if not stream_url:
            results["steps"][-1].update({"status": "failed", "error": "No stream URL found in metadata"})
            return results
        results["steps"][-1].update({"status": "success"})

        # Step 3: Head Request (Bot check on final URL)
        results["steps"].append({"name": "YouTube Connectivity", "status": "pending"})
        cookies = auth_state.get_cookies_for_aiohttp()
        target_headers = info.get('http_headers', {}).copy()
        ua = target_headers.get('User-Agent', '')
        if not ua or 'Googlebot' in ua or 'python' in ua.lower():
             target_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(cookies=cookies, timeout=timeout) as session:
            async with session.get(stream_url, headers=target_headers) as resp:
                if resp.status in [200, 206]:
                    results["steps"][-1].update({"status": "success", "http_status": resp.status})
                    results["success"] = True
                else:
                    results["steps"][-1].update({"status": "failed", "http_status": resp.status, "error": f"YouTube returned {resp.status}"})
                    
    except Exception as e:
        results["steps"].append({"name": "System Error", "status": "failed", "error": str(e)})
        
    return results

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

