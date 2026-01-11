
import yt_dlp
import logging
import json
import os
import tempfile
import asyncio
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the Cookies exactly as they are in main.py
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
        return None
        
    try:
        cookies = json.loads(cookies_env)
        
        # Create a temp file for cookies
        fd, path = tempfile.mkstemp(suffix='.txt', text=True) # file closed later manually for tests
        
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
print(f"Cookie file: {COOKIE_FILE}")

# The options we JUST committed to main.py
YDL_OPTS_AUDIO = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['android']}},
}

# if COOKIE_FILE:
#     YDL_OPTS_AUDIO['cookiefile'] = COOKIE_FILE

async def check_stream():
    # A video ID that failed in user logs
    url = "https://www.youtube.com/watch?v=ygsLpOwufoM"
    
    print(f"Attempting to extract: {url}")
    
    try:
        try:
             with yt_dlp.YoutubeDL(YDL_OPTS_AUDIO) as ydl:
                logger.info(f"Extracting info for {url}")
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            # Fallback chain: Try different clients without cookies if we get a "Sign in" or "Bot" error
            error_msg = str(e).lower()
            if any(s in error_msg for s in ["sign in", "bot", "403", "unsupported", "content is not available"]):
                 logger.warning(f"Strategy 1 failed ({e}), trying Fallback Strategies...")
                 
                 fallback_strategies = [
                     {'youtube': {'player_client': ['android']}},
                     {'youtube': {'player_client': ['mweb']}},
                     {'youtube': {'player_client': ['ios']}},
                 ]
                 
                 info = None
                 last_err = e
                 for strategy in fallback_strategies:
                     logger.info(f"Retrying with client strategy: {strategy['youtube']['player_client']}")
                     f_opts = YDL_OPTS_AUDIO.copy()
                     if 'cookiefile' in f_opts:
                         del f_opts['cookiefile']
                     f_opts['extractor_args'] = strategy
                     
                     try:
                         with yt_dlp.YoutubeDL(f_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                            if info:
                                logger.info(f"Success with strategy: {strategy['youtube']['player_client']}")
                                break
                     except Exception as fe:
                        logger.warning(f"Strategy {strategy['youtube']['player_client']} failed: {fe}")
                        last_err = fe
                 
                 if not info:
                     raise last_err
            else:
                raise e

        if not info:
            print("Failed to find info")
            return
            
        selected_format = None
        stream_url = info.get('url')
        
        if stream_url:
            selected_format = info
        else:
            formats = info.get('formats', [])
            selected_format = None
            for fmt in formats:
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    selected_format = fmt
                    break
            if not selected_format and formats:
                selected_format = formats[0]
            
            if selected_format:
                 stream_url = selected_format.get('url')

        if not stream_url:
            print("Failed to find stream URL")
            return

        print(f"Stream URL obtained: {stream_url[:50]}...")
            
            # Now try to FETCH it to see if we get 403
            # We must use similar headers to main.py
            target_headers = selected_format.get('http_headers', {}).copy() if selected_format else {}
            if not target_headers:
                 target_headers = {
                      'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                      'Accept': '*/*',
                 }
            
            target_headers['Range'] = 'bytes=0-1024'
            
            print(f"DEBUG: Headers keys: {list(target_headers.keys())}")
            print(f"DEBUG: User-Agent: {target_headers.get('User-Agent')}")

            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(stream_url, headers=target_headers) as resp:
                    print(f"Response Status: {resp.status}")
                    if resp.status == 403:
                        text = await resp.text()
                        print(f"403 Body: {text[:200]}")
                    elif resp.status == 200 or resp.status == 206:
                        print("SUCCESS! Stream is accessible.")
                    else:
                        print(f"Unexpected status: {resp.status}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_stream())
