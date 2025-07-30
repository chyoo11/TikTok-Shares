import requests
import time
import uuid
import random
import string
import re
import logging
import argparse
import os
import json
import base64
from datetime import datetime
from tqdm import tqdm
from io import BytesIO
from PIL import Image
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings for proxy connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_creator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ORANGE = '\033[38;5;208m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════╗
║  {Colors.MAGENTA}▪ ENHANCED INSTAGRAM CREATOR TOOL ▪{Colors.CYAN}         ║
╠══════════════════════════════════════════════╣
║  {Colors.GREEN}➤ Author   : {Colors.WHITE}EK6Q{Colors.CYAN}                     ║
║  {Colors.GREEN}➤ Tool     : {Colors.WHITE}Instagram Creator + Bio + PFP{Colors.CYAN}   ║
║  {Colors.GREEN}➤ Version  : {Colors.WHITE}5.0 - Anti-Detection{Colors.CYAN}           ║
╚══════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)

class ProxyManager:
    def __init__(self, proxy_file_path=None):
        self.proxies = []
        self.current_index = 0
        self.working_proxies = []
        self.failed_proxies = []
        self.max_retries = 3  # Limit retries to prevent infinite loops
        self.retry_count = 0
        
        if proxy_file_path:
            self.load_proxies(proxy_file_path)
    
    def load_proxies(self, file_path):
        """Load proxies from file"""
        try:
            if not os.path.exists(file_path):
                print(f"{Colors.RED}[!] Proxy file not found: {file_path}{Colors.RESET}")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy = self.parse_proxy(line)
                    if proxy:
                        self.proxies.append(proxy)
            
            print(f"{Colors.GREEN}[+] Loaded {len(self.proxies)} proxies from file{Colors.RESET}")
            return len(self.proxies) > 0
            
        except Exception as e:
            print(f"{Colors.RED}[!] Error loading proxies: {e}{Colors.RESET}")
            return False
    
    def parse_proxy(self, proxy_string):
        """Parse proxy string and return proxy dict - supports residential proxy formats"""
        try:
            original_string = proxy_string.strip()
            
            # Determine proxy type from original string
            proxy_type = 'http'
            if original_string.startswith('socks4://'):
                proxy_type = 'socks4'
                proxy_string = original_string.replace('socks4://', '')
            elif original_string.startswith('socks5://'):
                proxy_type = 'socks5'
                proxy_string = original_string.replace('socks5://', '')
            elif original_string.startswith('https://'):
                proxy_type = 'https'
                proxy_string = original_string.replace('https://', '')
            elif original_string.startswith('http://'):
                proxy_type = 'http'
                proxy_string = original_string.replace('http://', '')
            
            # Parse different formats
            if '@' in proxy_string:
                # Format: username:password@ip:port
                auth_part, server_part = proxy_string.split('@', 1)
                if ':' in auth_part:
                    username, password = auth_part.split(':', 1)
                else:
                    username, password = auth_part, ''
                
                if ':' in server_part:
                    ip, port = server_part.rsplit(':', 1)
                else:
                    print(f"{Colors.RED}[!] Invalid proxy format (missing port): {original_string}{Colors.RESET}")
                    return None
            else:
                # Format: ip:port or ip:port:username:password
                parts = proxy_string.split(':')
                if len(parts) == 2:
                    # ip:port (no auth)
                    ip, port = parts
                    username, password = '', ''
                elif len(parts) == 4:
                    # ip:port:username:password
                    ip, port, username, password = parts
                else:
                    print(f"{Colors.RED}[!] Invalid proxy format: {original_string}{Colors.RESET}")
                    return None
            
            # Validate port is numeric
            try:
                port = int(port)
            except ValueError:
                print(f"{Colors.RED}[!] Invalid port number: {port} in {original_string}{Colors.RESET}")
                return None
            
            return {
                'type': proxy_type,
                'ip': ip.strip(),
                'port': port,
                'username': username.strip(),
                'password': password.strip(),
                'string': original_string,
                'failed_count': 0
            }
            
        except Exception as e:
            print(f"{Colors.RED}[!] Error parsing proxy {proxy_string}: {e}{Colors.RESET}")
            return None
    
    def get_proxy_dict(self, proxy):
        """Convert proxy info to requests proxy dict"""
        if not proxy:
            return None
            
        auth_string = ""
        if proxy['username'] and proxy['password']:
            auth_string = f"{proxy['username']}:{proxy['password']}@"
        
        if proxy['type'] in ['socks4', 'socks5']:
            proxy_url = f"{proxy['type']}://{auth_string}{proxy['ip']}:{proxy['port']}"
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        else:
            proxy_url = f"http://{auth_string}{proxy['ip']}:{proxy['port']}"
            return {
                'http': proxy_url,
                'https': proxy_url
            }
    
    def test_proxy(self, proxy, timeout=20):
        """Test if proxy is working with multiple test URLs"""
        try:
            proxy_dict = self.get_proxy_dict(proxy)
            if not proxy_dict:
                return False
            
            # Test URLs - use multiple to increase reliability
            test_urls = [
                'http://httpbin.org/ip',
                'http://icanhazip.com',
                'http://ipinfo.io/ip'
            ]
            
            for test_url in test_urls:
                try:
                    response = requests.get(
                        test_url,
                        proxies=proxy_dict,
                        timeout=timeout,
                        verify=False,
                        headers={'User-Agent': generate_realistic_user_agent()}
                    )
                    
                    if response.status_code == 200:
                        # Try to get IP info
                        try:
                            if 'httpbin' in test_url:
                                ip_info = response.json()
                                current_ip = ip_info.get('origin', 'Unknown')
                            else:
                                current_ip = response.text.strip()
                            
                            print(f"{Colors.GREEN}[+] Proxy working: {proxy['ip']}:{proxy['port']} -> {current_ip[:50]}{Colors.RESET}")
                            return True
                        except:
                            print(f"{Colors.GREEN}[+] Proxy working: {proxy['ip']}:{proxy['port']}{Colors.RESET}")
                            return True
                            
                except requests.exceptions.RequestException:
                    continue
            
            return False
                
        except Exception as e:
            logger.debug(f"Proxy test failed for {proxy['ip']}:{proxy['port']}: {e}")
            return False
    
    def get_next_proxy(self):
        """Get next working proxy with improved retry logic"""
        if not self.proxies:
            return None
        
        # Reset retry count if we've gone through all proxies
        if self.retry_count >= self.max_retries:
            print(f"{Colors.RED}[!] Maximum proxy retries reached. No working proxies found.{Colors.RESET}")
            return None
        
        # Try to find a working proxy
        attempts = 0
        max_attempts = len(self.proxies) * 2  # Limit attempts to prevent infinite loops
        
        while attempts < max_attempts:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            attempts += 1
            
            # Skip proxies that have failed too many times
            if proxy.get('failed_count', 0) >= 3:
                continue
            
            # Check if proxy is in failed list
            if proxy in self.failed_proxies:
                continue
            
            # Test proxy if not in working list
            if proxy not in self.working_proxies:
                print(f"{Colors.YELLOW}[*] Testing proxy: {proxy['ip']}:{proxy['port']}{Colors.RESET}")
                if self.test_proxy(proxy):
                    self.working_proxies.append(proxy)
                    proxy['failed_count'] = 0
                    return proxy
                else:
                    self.failed_proxies.append(proxy)
                    proxy['failed_count'] = proxy.get('failed_count', 0) + 1
                    print(f"{Colors.RED}[!] Proxy failed: {proxy['ip']}:{proxy['port']}{Colors.RESET}")
                    continue
            else:
                return proxy
        
        # If no working proxies found, increment retry count and try failed ones once more
        if self.failed_proxies and self.retry_count < self.max_retries:
            self.retry_count += 1
            print(f"{Colors.YELLOW}[*] Retry attempt {self.retry_count}/{self.max_retries} - Testing failed proxies...{Colors.RESET}")
            
            # Reset failed proxies for one more try
            for proxy in self.failed_proxies[:]:
                if proxy.get('failed_count', 0) < 2:  # Only retry proxies that haven't failed too much
                    self.failed_proxies.remove(proxy)
            
            if self.failed_proxies:
                return self.get_next_proxy()
        
        print(f"{Colors.RED}[!] No working proxies available. Continuing without proxy...{Colors.RESET}")
        return None

def generate_random_string(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

def generate_realistic_user_agent():
    """Generate realistic user agents with proper browser versions"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ]
    return random.choice(user_agents)

def generate_user_agent():
    mobile_agents = [
        "Instagram 237.0.0.14.102 Android (33/13; 300dpi; 720x1467; samsung; SM-A127F; a12s; exynos850; en_GB; 373310554)",
        "Instagram 243.0.0.12.111 Android (32/12; 320dpi; 720x1520; xiaomi; Redmi Note 9; merlin; mt6768; en_US; 373310554)",
        "Instagram 240.1.0.19.109 Android (31/11; 280dpi; 720x1440; huawei; ANA-LX4; anna; kirin710; en_GB; 373310554)"
    ]
    return random.choice(mobile_agents)

def generate_web_user_agent():
    return generate_realistic_user_agent()

def generate_random_bio():
    bios = [
        "Living my best life ✨",
        "Dream big, work hard 💪",
        "Creating memories 📸",
        "Just enjoying the journey 🌟",
        "Life is beautiful 🌺",
        "Stay positive, stay strong 💫",
        "Making every moment count ⏰",
        "Blessed and grateful 🙏",
        "Chasing dreams and sunsets 🌅",
        "Living life to the fullest 🎉",
        "Good vibes only ✌️",
        "Adventure awaits 🗺️",
        "Smile more, worry less 😊",
        "Be yourself, everyone else is taken 💯",
        "Life's too short to be ordinary 🚀",
        "Coffee lover ☕",
        "Wanderlust soul 🌍",
        "Music is life 🎵",
        "Fitness enthusiast 💪",
        "Foodie adventures 🍕"
    ]
    return random.choice(bios)

def create_random_profile_picture():
    """Create a simple colored square as profile picture"""
    try:
        # Create a 400x400 image with random color
        colors = [
            (255, 99, 132),   # Pink
            (54, 162, 235),   # Blue
            (255, 205, 86),   # Yellow
            (75, 192, 192),   # Teal
            (153, 102, 255),  # Purple
            (255, 159, 64),   # Orange
            (199, 199, 199),  # Grey
            (83, 102, 255),   # Indigo
        ]
        
        color = random.choice(colors)
        img = Image.new('RGB', (400, 400), color)
        
        # Save to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG', quality=95)
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
    except Exception as e:
        logger.error(f"Error creating profile picture: {e}")
        return None

def get_temp_email():
    try:
        print(f"{Colors.YELLOW}[*] Creating temporary email...{Colors.RESET}")
        resp = requests.get("https://api.guerrillamail.com/ajax.php?f=get_email_address", timeout=15)
        if resp.status_code != 200:
            logger.error(f"Failed to create temporary email. Response code: {resp.status_code}")
            return None, None

        data = resp.json()
        email_addr = data.get("email_addr")
        sid_token = data.get("sid_token")
        return email_addr, sid_token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating temporary email: {e}")
        return None, None

def poll_for_verification_code(sid_token, max_retries=25, delay=6):
    base_url = "https://api.guerrillamail.com/ajax.php"

    print(f"\n{Colors.CYAN}[*] Waiting for verification code from Instagram...{Colors.RESET}")
    pbar = tqdm(total=max_retries, desc="Searching for code", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} attempts")

    for retry in range(max_retries):
        try:
            pbar.update(1)

            mailbox_resp = requests.get(f"{base_url}?f=get_email_list&offset=0&sid_token={sid_token}", timeout=15)
            if mailbox_resp.status_code != 200:
                logger.warning(f"Failed to fetch messages. Response code: {mailbox_resp.status_code}")
                time.sleep(delay)
                continue

            mailbox_data = mailbox_resp.json()
            messages = mailbox_data.get("list", [])

            for msg in messages:
                subject = msg.get("mail_subject", "")
                mail_from = msg.get("mail_from", "")
                if "Instagram" in subject or "instagram" in mail_from.lower():
                    mail_id = msg.get("mail_id")

                    detail_resp = requests.get(f"{base_url}?f=fetch_email&sid_token={sid_token}&email_id={mail_id}", timeout=15)
                    if detail_resp.status_code != 200:
                        continue

                    detail_data = detail_resp.json()
                    mail_body = detail_data.get("mail_body", "")

                    code_match = re.search(r'\b\d{4,6}\b', mail_body)
                    if code_match:
                        pbar.close()
                        print(f"{Colors.GREEN}[+] Verification code found!{Colors.RESET}")
                        return code_match.group(0)

            time.sleep(delay)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error while searching for verification code: {e}")
            time.sleep(delay)

    pbar.close()
    print(f"{Colors.RED}[!] Timeout waiting for verification code{Colors.RESET}")
    logger.error("Timeout waiting for verification code")
    return None

def generate_random_name():
    first_names = ["أحمد", "محمد", "سارة", "فاطمة", "نور", "علي", "عمر", "مريم", "حسن", "ليلى",
                   "Alex", "Emma", "Noah", "Sophia", "Liam", "Olivia", "John", "Zoe", "Ryan", "Lily",
                   "James", "Isabella", "William", "Charlotte", "Benjamin", "Amelia", "Lucas", "Mia",
                   "Henry", "Harper", "Alexander", "Evelyn", "Mason", "Abigail", "Michael", "Emily"]
    return random.choice(first_names)

def generate_random_birthday():
    current_year = datetime.now().year
    year = random.randint(current_year - 45, current_year - 18)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return day, month, year

def human_delay(min_seconds=2, max_seconds=8):
    """Add human-like delay between actions"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def get_csrf_token(session):
    """Get fresh CSRF token from Instagram"""
    try:
        # Add human-like delay before getting token
        human_delay(1, 3)
        
        response = session.get("https://www.instagram.com/accounts/signup/email/", timeout=20)
        csrf_match = re.search(r'"csrf_token":"([^"]+)"', response.text)
        if csrf_match:
            return csrf_match.group(1)
        
        # Try alternative method
        csrf_match2 = re.search(r'csrftoken=([^;]+)', response.headers.get('set-cookie', ''))
        if csrf_match2:
            return csrf_match2.group(1)
            
        return None
    except Exception as e:
        logger.error(f"Error getting CSRF token: {e}")
        return None

def warm_up_session(session):
    """Warm up session by visiting Instagram pages like a real user"""
    try:
        print(f"{Colors.YELLOW}[*] Warming up session...{Colors.RESET}")
        
        # Visit Instagram homepage
        session.get("https://www.instagram.com/", timeout=20)
        human_delay(2, 4)
        
        # Visit login page
        session.get("https://www.instagram.com/accounts/login/", timeout=20)
        human_delay(1, 3)
        
        # Visit signup page
        session.get("https://www.instagram.com/accounts/signup/", timeout=20)
        human_delay(2, 5)
        
        print(f"{Colors.GREEN}[+] Session warmed up successfully{Colors.RESET}")
        return True
        
    except Exception as e:
        logger.error(f"Error warming up session: {e}")
        return False

def create_session_with_proxy(proxy_manager):
    """Create a requests session with proxy configuration and realistic settings"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set proxy if available
    if proxy_manager:
        proxy = proxy_manager.get_next_proxy()
        if proxy:
            proxy_dict = proxy_manager.get_proxy_dict(proxy)
            if proxy_dict:
                session.proxies.update(proxy_dict)
                print(f"{Colors.CYAN}[*] Using proxy: {proxy['ip']}:{proxy['port']}{Colors.RESET}")
                
                # Add authentication headers if needed
                if proxy['username'] and proxy['password']:
                    print(f"{Colors.CYAN}[*] Proxy authentication: {proxy['username']}:{'*' * len(proxy['password'])}{Colors.RESET}")
                
                # Test the proxy with the session
                try:
                    test_response = session.get('http://httpbin.org/ip', timeout=15, verify=False)
                    if test_response.status_code == 200:
                        try:
                            ip_info = test_response.json()
                            current_ip = ip_info.get('origin', 'Unknown')
                            print(f"{Colors.GREEN}[+] Session proxy verified: {current_ip}{Colors.RESET}")
                        except:
                            print(f"{Colors.GREEN}[+] Session proxy verified{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}[*] Proxy verification failed, but continuing...{Colors.RESET}")
                except Exception as e:
                    print(f"{Colors.YELLOW}[*] Proxy verification error: {str(e)[:50]}...{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}[*] No working proxy available, using direct connection{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[*] No proxy available, using direct connection{Colors.RESET}")
    
    # Disable SSL verification for proxy connections
    session.verify = False
    
    # Set realistic timeout
    session.timeout = 30
    
    return session

class InstagramAccountCreator:
    def __init__(self, save_to_file=True, proxy_manager=None):
        self.save_to_file = save_to_file
        self.success_count = 0
        self.fail_count = 0
        self.proxy_manager = proxy_manager

    def upload_profile_picture(self, session, session_id, user_id, device_id, uuid_val):
        """Upload profile picture after account creation"""
        try:
            print(f"{Colors.YELLOW}[*] Uploading profile picture...{Colors.RESET}")
            
            # Create random profile picture
            img_data = create_random_profile_picture()
            if not img_data:
                print(f"{Colors.RED}[!] Failed to create profile picture{Colors.RESET}")
                return False

            # First, upload the image
            upload_id = str(int(time.time() * 1000))
            
            # Upload image to Instagram servers
            upload_url = "https://b.i.instagram.com/rupload_igphoto/fb_uploader_" + upload_id
            
            upload_headers = {
                'User-Agent': generate_user_agent(),
                'Accept-Encoding': "zstd, gzip, deflate",
                'x-ig-app-locale': "en_GB",
                'x-ig-device-locale': "en_GB",
                'x-ig-mapped-locale': "en_GB",
                'x-pigeon-session-id': f"UFS-{uuid.uuid4()}",
                'x-pigeon-rawclienttime': str(time.time()),
                'x-ig-bandwidth-speed-kbps': "-1.000",
                'x-ig-bandwidth-totalbytes-b': "0",
                'x-ig-bandwidth-totaltime-ms': "0",
                'x-ig-app-startup-country': "US",
                'x-bloks-version-id': "8dab28e76d3286a104a7f1c9e0c632386603a488cf584c9b49161c2f5182fe07",
                'x-ig-www-claim': "hmac.AR1Nk-vHGyWCQhIRNBem0c6fUsdHQD_VD4st9zlF0GLHTyhS",
                'x-bloks-is-layout-rtl': "false",
                'x-ig-device-id': uuid_val,
                'x-ig-family-device-id': str(uuid.uuid4()),
                'x-ig-android-id': device_id,
                'x-ig-timezone-offset': "0",
                'x-fb-connection-type': "WIFI",
                'x-ig-connection-type': "WIFI",
                'x-ig-capabilities': "3brTv10=",
                'x-ig-app-id': "567067343352427",
                'authorization': f"Bearer IGT:2:{{\"ds_user_id\":\"{user_id}\",\"sessionid\":\"{session_id}\"}}",
                'x-mid': f"Y{generate_random_string(10)}",
                'ig-u-ds-user-id': user_id,
                'ig-intended-user-id': user_id,
                'x-fb-http-engine': "Liger",
                'x-fb-client-ip': "True",
                'x-fb-server-cluster': "True",
                'Content-Type': "image/jpeg",
                'Content-Length': str(len(img_data)),
                'X-Entity-Name': f"fb_uploader_{upload_id}",
                'Offset': "0",
                'X-Instagram-Rupload-Params': json.dumps({
                    "upload_id": upload_id,
                    "media_type": "1",
                    "sticker_burnin_params": "[]",
                    "image_compression": json.dumps({"lib_name": "moz", "lib_version": "3.1.m", "quality": "95"}),
                    "xsharing_user_ids": "[]",
                    "retry_context": json.dumps({"num_step_auto_retry": 0, "num_reupload": 0, "num_step_manual_retry": 0}),
                    "IG-FB-Xpost-entry-point-v2": "feed"
                })
            }

            # Upload the image using the same session
            upload_response = session.post(upload_url, data=img_data, headers=upload_headers, timeout=30)
            
            if upload_response.status_code not in [200, 201]:
                print(f"{Colors.RED}[!] Failed to upload image. Status: {upload_response.status_code}{Colors.RESET}")
                return False

            # Wait before setting profile picture
            human_delay(3, 6)

            # Now set it as profile picture
            change_pic_url = "https://b.i.instagram.com/api/v1/accounts/change_profile_picture/"
            
            change_pic_payload = {
                '_uuid': uuid_val,
                'use_fbuploader': "true",
                'upload_id': upload_id
            }

            change_pic_headers = {
                'User-Agent': generate_user_agent(),
                'Accept-Encoding': "zstd, gzip, deflate",
                'x-ig-app-locale': "en_GB",
                'x-ig-device-locale': "en_GB",
                'x-ig-mapped-locale': "en_GB",
                'x-pigeon-session-id': f"UFS-{uuid.uuid4()}",
                'x-pigeon-rawclienttime': str(time.time()),
                'x-ig-bandwidth-speed-kbps': "-1.000",
                'x-ig-bandwidth-totalbytes-b': "0",
                'x-ig-bandwidth-totaltime-ms': "0",
                'x-ig-app-startup-country': "US",
                'x-bloks-version-id': "8dab28e76d3286a104a7f1c9e0c632386603a488cf584c9b49161c2f5182fe07",
                'x-ig-www-claim': "hmac.AR1Nk-vHGyWCQhIRNBem0c6fUsdHQD_VD4st9zlF0GLHTyhS",
                'x-bloks-is-layout-rtl': "false",
                'x-ig-device-id': uuid_val,
                'x-ig-family-device-id': str(uuid.uuid4()),
                'x-ig-android-id': device_id,
                'x-ig-timezone-offset': "0",
                'x-ig-nav-chain': "AjV:self_profile:4:main_profile::,MediaCaptureFragment:tabbed_gallery_camera:8:new_profile_photo::,MediaCaptureFragment:tabbed_gallery_camera:9:button::,83Z:photo_filter:10:button::,AjV:self_profile:11:button::",
                'x-fb-connection-type': "WIFI",
                'x-ig-connection-type': "WIFI",
                'x-ig-capabilities': "3brTv10=",
                'x-ig-app-id': "567067343352427",
                'priority': "u=3",
                'accept-language': "en-GB, en-US",
                'authorization': f"Bearer IGT:2:{{\"ds_user_id\":\"{user_id}\",\"sessionid\":\"{session_id}\"}}",
                'x-mid': f"Y{generate_random_string(10)}",
                'ig-u-ds-user-id': user_id,
                'ig-u-rur': f"RVA,{user_id},{int(time.time()) + 86400}:01fe{generate_random_string(60)}",
                'ig-intended-user-id': user_id,
                'x-fb-http-engine': "Liger",
                'x-fb-client-ip': "True",
                'x-fb-server-cluster': "True"
            }

            change_response = session.post(change_pic_url, data=change_pic_payload, headers=change_pic_headers, timeout=30)
            
            if '"status":"ok"' in change_response.text or change_response.status_code == 200:
                print(f"{Colors.GREEN}[+] Profile picture uploaded successfully!{Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}[!] Failed to set profile picture: {change_response.text[:100]}{Colors.RESET}")
                return False

        except Exception as e:
            print(f"{Colors.RED}[!] Error uploading profile picture: {e}{Colors.RESET}")
            logger.error(f"Error uploading profile picture: {e}")
            return False

    def set_biography(self, session, session_id, user_id, device_id, uuid_val, bio_text):
        """Set biography after account creation"""
        try:
            print(f"{Colors.YELLOW}[*] Setting biography...{Colors.RESET}")
            
            url = "https://b.i.instagram.com/api/v1/accounts/set_biography/"
            
            signed_body_data = {
                "_uid": user_id,
                "device_id": device_id,
                "_uuid": uuid_val,
                "raw_text": bio_text
            }
            
            signed_body = "SIGNATURE." + json.dumps(signed_body_data)
            
            payload = {
                'signed_body': signed_body
            }

            headers = {
                'User-Agent': generate_user_agent(),
                'Accept-Encoding': "zstd, gzip, deflate",
                'x-ig-app-locale': "en_GB",
                'x-ig-device-locale': "en_GB",
                'x-ig-mapped-locale': "en_GB",
                'x-pigeon-session-id': f"UFS-{uuid.uuid4()}",
                'x-pigeon-rawclienttime': str(time.time()),
                'x-ig-bandwidth-speed-kbps': "-1.000",
                'x-ig-bandwidth-totalbytes-b': "0",
                'x-ig-bandwidth-totaltime-ms': "0",
                'x-ig-app-startup-country': "US",
                'x-bloks-version-id': "8dab28e76d3286a104a7f1c9e0c632386603a488cf584c9b49161c2f5182fe07",
                'x-ig-www-claim': "hmac.AR1Nk-vHGyWCQhIRNBem0c6fUsdHQD_VD4st9zlF0GLHTyhS",
                'x-bloks-is-layout-rtl': "false",
                'x-ig-device-id': uuid_val,
                'x-ig-family-device-id': str(uuid.uuid4()),
                'x-ig-android-id': device_id,
                'x-ig-timezone-offset': "0",
                'x-ig-nav-chain': "AjV:self_profile:4:main_profile::,AYg:edit_profile:5:button::,EE9:profile_edit_bio:6:button::,EE9:profile_edit_bio:7:button::",
                'x-fb-connection-type': "WIFI",
                'x-ig-connection-type': "WIFI",
                'x-ig-capabilities': "3brTv10=",
                'x-ig-app-id': "567067343352427",
                'priority': "u=3",
                'accept-language': "en-GB, en-US",
                'authorization': f"Bearer IGT:2:{{\"ds_user_id\":\"{user_id}\",\"sessionid\":\"{session_id}\"}}",
                'x-mid': f"Y{generate_random_string(10)}",
                'ig-u-ds-user-id': user_id,
                'ig-u-rur': f"RVA,{user_id},{int(time.time()) + 86400}:01fe{generate_random_string(60)}",
                'ig-intended-user-id': user_id,
                'x-fb-http-engine': "Liger",
                'x-fb-client-ip': "True",
                'x-fb-server-cluster': "True"
            }

            response = session.post(url, data=payload, headers=headers, timeout=30)
            
            if '"status":"ok"' in response.text or response.status_code == 200:
                print(f"{Colors.GREEN}[+] Biography set successfully: {Colors.CYAN}{bio_text}{Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}[!] Failed to set biography: {response.text[:100]}{Colors.RESET}")
                return False

        except Exception as e:
            print(f"{Colors.RED}[!] Error setting biography: {e}{Colors.RESET}")
            logger.error(f"Error setting biography: {e}")
            return False

    def create_account(self):
        logger.info("Starting account creation process...")

        device_id = f"android-{generate_random_string(16)}"
        uuid_val = str(uuid.uuid4())

        st4_user_agent = generate_web_user_agent()
        st4_time = str(time.time()).split('.')[1]

        # Create a session with proxy
        st4_session = create_session_with_proxy(self.proxy_manager)
        
        # Set realistic headers
        st4_session.headers.update({
            'User-Agent': st4_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

        # Warm up session first
        if not warm_up_session(st4_session):
            print(f"{Colors.YELLOW}[*] Session warm-up failed, continuing anyway...{Colors.RESET}")

        email, sid_token = get_temp_email()
        if not email or not sid_token:
            print(f"{Colors.RED}[!] Failed to obtain temporary email{Colors.RESET}")
            self.fail_count += 1
            return False

        print(f"{Colors.GREEN}[+] Created temporary email: {Colors.CYAN}{email}{Colors.RESET}")
        logger.info(f"Created temporary email: {email}")

        # Get fresh CSRF token
        print(f"{Colors.YELLOW}[*] Getting CSRF token...{Colors.RESET}")
        csrf_token = get_csrf_token(st4_session)
        if not csrf_token:
            csrf_token = generate_random_string(32)  # Fallback
            
        print(f"{Colors.GREEN}[+] CSRF token obtained{Colors.RESET}")

        # Add delay before email check
        human_delay(3, 7)

        print(f"{Colors.YELLOW}[*] Checking email availability...{Colors.RESET}")
        url = "https://www.instagram.com/api/v1/web/accounts/check_email/"
        payload = {
            'email': email,
        }
        
        # Generate more realistic headers
        ajax_id = str(random.randint(1000000000, 9999999999))
        session_id = f"{generate_random_string(6)}:{generate_random_string(6)}:{generate_random_string(6)}"
        
        headers = {
            'User-Agent': st4_user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf_token,
            'X-IG-App-ID': '1217981644879628',
            'X-IG-WWW-Claim': '0',
            'X-Instagram-AJAX': ajax_id,
            'X-ASBD-ID': '359341',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/accounts/signup/email/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }

        try:
            response = st4_session.post(url, data=payload, headers=headers, timeout=25).text
            if '"available":true' not in response:
                print(f"{Colors.RED}[!] Email not available{Colors.RESET}")
                logger.error(f"Email not available: {response}")
                
                # Check if it's a rate limit issue
                if "feedback_required" in response or "spam" in response:
                    print(f"{Colors.YELLOW}[*] Rate limited, waiting longer before retry...{Colors.RESET}")
                    time.sleep(random.randint(30, 60))
                
                self.fail_count += 1
                return False

            print(f"{Colors.GREEN}[+] Email availability check passed{Colors.RESET}")
            logger.info("Email availability check passed")
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}[!] Error during email check: {e}{Colors.RESET}")
            logger.error(f"Error during email check: {e}")
            self.fail_count += 1
            return False

        # Add delay before sending verification email
        human_delay(4, 8)

        print(f"{Colors.YELLOW}[*] Sending verification email...{Colors.RESET}")
        url = "https://www.instagram.com/api/v1/accounts/send_verify_email/"
        payload = {
            'device_id': device_id,
            'email': email,
        }

        try:
            response = st4_session.post(url, data=payload, headers=headers, timeout=25).text
            if '"email_sent":true' not in response:
                print(f"{Colors.RED}[!] Failed to send verification email{Colors.RESET}")
                logger.error(f"Failed to send verification email: {response}")
                self.fail_count += 1
                return False

            print(f"{Colors.GREEN}[+] Verification email sent successfully{Colors.RESET}")
            logger.info("Verification email sent successfully")
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}[!] Error sending verification email: {e}{Colors.RESET}")
            logger.error(f"Error sending verification email: {e}")
            self.fail_count += 1
            return False

        st4_code = poll_for_verification_code(sid_token)
        if not st4_code:
            print(f"{Colors.RED}[!] Failed to get verification code{Colors.RESET}")
            logger.error("Failed to get verification code")
            self.fail_count += 1
            return False

        print(f"{Colors.GREEN}[+] Received verification code: {Colors.CYAN}{st4_code}{Colors.RESET}")
        logger.info(f"Received verification code: {st4_code}")

        # Add delay before validating code
        human_delay(2, 5)

        print(f"{Colors.YELLOW}[*] Validating confirmation code...{Colors.RESET}")
        url = "https://www.instagram.com/api/v1/accounts/check_confirmation_code/"
        payload = {
            'code': st4_code,
            'device_id': device_id,
            'email': email,
        }

        try:
            response = st4_session.post(url, data=payload, headers=headers, timeout=25)
            try:
                st4_newCode = response.json()['signup_code']
                print(f"{Colors.GREEN}[+] Confirmation code validated successfully{Colors.RESET}")
                logger.info("Confirmation code validated successfully")
            except Exception as e:
                print(f"{Colors.RED}[!] Failed to get signup code: {e}{Colors.RESET}")
                logger.error(f"Failed to get signup code: {e}")
                self.fail_count += 1
                return False
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}[!] Error checking confirmation code: {e}{Colors.RESET}")
            logger.error(f"Error checking confirmation code: {e}")
            self.fail_count += 1
            return False

        print(f"{Colors.YELLOW}[*] Generating account details...{Colors.RESET}")
        st4_password = ''.join(random.choice(string.ascii_letters + string.digits + '!@#$%^&*()') for _ in range(12))
        username = f"user_{generate_random_string(8).lower()}"
        st4_first_name = generate_random_name()
        st4_day, st4_month, st4_year = generate_random_birthday()

        # Add delay before account creation
        human_delay(5, 10)

        print(f"{Colors.YELLOW}[*] Creating Instagram account...{Colors.RESET}")
        url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/"
        payload = {
            'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{st4_time}:{st4_password}",
            'day': st4_day,
            'email': email,
            'failed_birthday_year_count': "{}",
            'first_name': st4_first_name,
            'month': st4_month,
            'username': username,
            'year': st4_year,
            'client_id': device_id,
            'seamless_login_enabled': "1",
            'tos_version': "row",
            'force_sign_up_code': st4_newCode,
        }

        try:
            response = st4_session.post(url, data=payload, headers=headers, timeout=30)

            if '"account_created":true' not in response.text:
                print(f"{Colors.RED}[!] Account creation failed{Colors.RESET}")
                logger.error(f"Account creation failed: {response.text}")
                self.fail_count += 1
                return False

            ST4_SESSION = response.cookies.get_dict().get('sessionid')
            if not ST4_SESSION:
                print(f"{Colors.RED}[!] Failed to get session ID{Colors.RESET}")
                logger.error("Failed to get session ID")
                self.fail_count += 1
                return False

            # Extract user ID from response
            try:
                response_json = response.json()
                user_id = str(response_json.get('user_id', ''))
                if not user_id:
                    # Try to extract from response text
                    user_id_match = re.search(r'"user_id":(\d+)', response.text)
                    if user_id_match:
                        user_id = user_id_match.group(1)
                    else:
                        user_id = str(random.randint(100000000, 999999999))
            except:
                user_id = str(random.randint(100000000, 999999999))

            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ACCOUNT CREATED SUCCESSFULLY! ✅{Colors.RESET}\n")

            # Wait longer before setting bio and profile picture to ensure session is stable
            print(f"{Colors.YELLOW}[*] Waiting 15 seconds for account initialization...{Colors.RESET}")
            time.sleep(15)

            # Generate random bio
            bio_text = generate_random_bio()

            # Set biography using the same session
            bio_success = self.set_biography(st4_session, ST4_SESSION, user_id, device_id, uuid_val, bio_text)

            # Wait before uploading profile picture
            human_delay(8, 15)

            # Upload profile picture using the same session
            pic_success = self.upload_profile_picture(st4_session, ST4_SESSION, user_id, device_id, uuid_val)

            account_info = [
                f"{Colors.CYAN}╔{'═' * 60}╗",
                f"║ {Colors.GREEN}ENHANCED INSTAGRAM ACCOUNT DETAILS{Colors.CYAN}{' ' * 26}║",
                f"╠{'═' * 60}╣",
                f"║ {Colors.YELLOW}• Username:{Colors.WHITE}{' ' * (51 - len(username))}{username}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Password:{Colors.WHITE}{' ' * (51 - len(st4_password))}{st4_password}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Email:{Colors.WHITE}{' ' * (54 - len(email))}{email}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• First Name:{Colors.WHITE}{' ' * (49 - len(st4_first_name))}{st4_first_name}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Birthday:{Colors.WHITE}{' ' * (43)}{st4_year}-{st4_month}-{st4_day}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• User ID:{Colors.WHITE}{' ' * (52 - len(user_id))}{user_id}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Session ID:{Colors.WHITE}{' ' * (50 - len(ST4_SESSION[:10]))}{ST4_SESSION[:10]}...{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Biography:{Colors.WHITE}{' ' * (50 - len(bio_text))}{bio_text}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Bio Status:{Colors.WHITE}{' ' * (45)}{'✅ Success' if bio_success else '❌ Failed'}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Profile Pic:{Colors.WHITE}{' ' * (44)}{'✅ Success' if pic_success else '❌ Failed'}{Colors.CYAN} ║",
                f"║ {Colors.YELLOW}• Created At:{Colors.WHITE}{' ' * (40)}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.CYAN} ║",
                f"╚{'═' * 60}╝{Colors.RESET}"
            ]

            for line in account_info:
                print(line)

            logger.info("Account created successfully!")

            if self.save_to_file:
                with open("ACC_SESSIONS_IG.txt", "a") as f:
                    f.write(f"{ST4_SESSION}\n")

                with open("instagram_accounts.txt", "a", encoding="utf-8") as f:
                    f.write(f"Username: {username}\n")
                    f.write(f"Password: {st4_password}\n")
                    f.write(f"Email: {email}\n")
                    f.write(f"First Name: {st4_first_name}\n")
                    f.write(f"Birthday: {st4_year}-{st4_month}-{st4_day}\n")
                    f.write(f"User ID: {user_id}\n")
                    f.write(f"Session ID: {ST4_SESSION}\n")
                    f.write(f"Biography: {bio_text}\n")
                    f.write(f"Bio Status: {'Success' if bio_success else 'Failed'}\n")
                    f.write(f"Profile Pic: {'Success' if pic_success else 'Failed'}\n")
                    f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 70 + "\n")

                print(f"\n{Colors.GREEN}[+] Account details saved to 'instagram_accounts.txt'{Colors.RESET}")
                print(f"{Colors.GREEN}[+] Session ID saved to 'ACC_SESSIONS_IG.txt'{Colors.RESET}")

            self.success_count += 1
            return True

        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}[!] Error during account creation: {e}{Colors.RESET}")
            logger.error(f"Error during account creation: {e}")
            self.fail_count += 1
            return False

def display_proxy_formats():
    """Display supported proxy formats"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}📋 SUPPORTED PROXY FORMATS:{Colors.RESET}")
    print(f"{Colors.YELLOW}HTTP/HTTPS Proxies:{Colors.RESET}")
    print(f"  • ip:port")
    print(f"  • ip:port:username:password")
    print(f"  • username:password@ip:port")
    print(f"  • http://ip:port")
    print(f"  • https://username:password@ip:port")
    
    print(f"\n{Colors.YELLOW}SOCKS Proxies:{Colors.RESET}")
    print(f"  • socks4://ip:port")
    print(f"  • socks5://ip:port")
    print(f"  • socks4://username:password@ip:port")
    print(f"  • socks5://username:password@ip:port")
    
    print(f"\n{Colors.YELLOW}Residential Proxy Examples:{Colors.RESET}")
    print(f"  • b006765d7dc8c60a.iuy.us.ip2world.vip:6001:username:password")
    print(f"  • username:password@residential.proxy.com:8000")
    print(f"  • http://user:pass@premium.proxy.net:3128")
    
    print(f"\n{Colors.GREEN}💡 Tips:{Colors.RESET}")
    print(f"  • One proxy per line")
    print(f"  • Lines starting with # are ignored (comments)")
    print(f"  • Make sure username/password are correct for residential proxies")
    print(f"  • Test your proxies first with a simple tool")

def get_user_input():
    try:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}How many Instagram accounts do you want to create?{Colors.RESET}")
        while True:
            try:
                count = int(input(f"{Colors.CYAN}Enter number (1-50): {Colors.RESET}"))
                if 1 <= count <= 50:
                    break
                print(f"{Colors.RED}Please enter a number between 1 and 50.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")

        print(f"\n{Colors.YELLOW}{Colors.BOLD}Do you want to use proxies?{Colors.RESET}")
        use_proxy = input(f"{Colors.CYAN}Use proxies? (Y/n): {Colors.RESET}").lower()
        use_proxy = use_proxy != 'n' and use_proxy != 'no'
        
        proxy_manager = None
        if use_proxy:
            while True:
                proxy_file = input(f"{Colors.CYAN}Enter proxy file path (or 'help' for formats, Enter to skip): {Colors.RESET}").strip()
                
                if proxy_file.lower() == 'help':
                    display_proxy_formats()
                    continue
                elif not proxy_file:
                    print(f"{Colors.YELLOW}[*] Skipping proxy usage{Colors.RESET}")
                    break
                
                proxy_manager = ProxyManager(proxy_file)
                if proxy_manager.proxies:
                    print(f"{Colors.GREEN}[+] Proxy manager initialized with {len(proxy_manager.proxies)} proxies{Colors.RESET}")
                    
                    # Test a few proxies to make sure they work
                    print(f"{Colors.YELLOW}[*] Testing first few proxies...{Colors.RESET}")
                    working_count = 0
                    for i, proxy in enumerate(proxy_manager.proxies[:3]):  # Test first 3
                        if proxy_manager.test_proxy(proxy):
                            working_count += 1
                    
                    if working_count > 0:
                        print(f"{Colors.GREEN}[+] {working_count}/3 test proxies are working{Colors.RESET}")
                        break
                    else:
                        print(f"{Colors.RED}[!] No test proxies are working. Please check your proxy format and credentials.{Colors.RESET}")
                        display_proxy_formats()
                        retry = input(f"{Colors.CYAN}Try again? (Y/n): {Colors.RESET}").lower()
                        if retry == 'n' or retry == 'no':
                            proxy_manager = None
                            break
                else:
                    print(f"{Colors.RED}[!] Failed to load proxies. Please check the file path and format.{Colors.RESET}")
                    display_proxy_formats()
                    retry = input(f"{Colors.CYAN}Try again? (Y/n): {Colors.RESET}").lower()
                    if retry == 'n' or retry == 'no':
                        break

        print(f"\n{Colors.YELLOW}{Colors.BOLD}Delay between account creations (seconds):{Colors.RESET}")
        while True:
            try:
                delay = int(input(f"{Colors.CYAN}Enter delay (30-300): {Colors.RESET}"))
                if 30 <= delay <= 300:
                    break
                print(f"{Colors.RED}Please enter a number between 30 and 300.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")

        print(f"\n{Colors.YELLOW}{Colors.BOLD}Save accounts to file?{Colors.RESET}")
        while True:
            save = input(f"{Colors.CYAN}Save to file? (Y/n): {Colors.RESET}").lower()
            if save in ['', 'y', 'yes', 'n', 'no']:
                save_to_file = save != 'n' and save != 'no'
                break
            print(f"{Colors.RED}Please enter Y or N.{Colors.RESET}")

        return count, delay, save_to_file, proxy_manager
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Operation cancelled by user.{Colors.RESET}")
        exit(0)

def main():
    try:
        clear_screen()
        display_banner()

        count, delay, save_to_file, proxy_manager = get_user_input()

        print("\n" + "=" * 70)
        print(f"{Colors.GREEN}Starting Enhanced Instagram Account Creator v5.0{Colors.RESET}")
        print(f"{Colors.CYAN}• Creating {Colors.WHITE}{count}{Colors.CYAN} account(s) with bio and profile picture{Colors.RESET}")
        print(f"{Colors.CYAN}• Delay between accounts: {Colors.WHITE}{delay}{Colors.CYAN} seconds{Colors.RESET}")
        print(f"{Colors.CYAN}• Save to file: {Colors.WHITE}{'Yes' if save_to_file else 'No'}{Colors.RESET}")
        print(f"{Colors.CYAN}• Using proxies: {Colors.WHITE}{'Yes' if proxy_manager else 'No'}{Colors.RESET}")
        if proxy_manager:
            print(f"{Colors.CYAN}• Total proxies loaded: {Colors.WHITE}{len(proxy_manager.proxies)}{Colors.RESET}")
        print(f"{Colors.CYAN}• Anti-detection: {Colors.WHITE}Enabled{Colors.RESET}")
        print("=" * 70)

        creator = InstagramAccountCreator(save_to_file=save_to_file, proxy_manager=proxy_manager)

        for i in range(count):
            print(f"\n{Colors.CYAN}{Colors.BOLD}[{i+1}/{count}] Creating Instagram account with full profile...{Colors.RESET}\n")
            result = creator.create_account()

            if i < count - 1:
                print(f"\n{Colors.YELLOW}Waiting {delay} seconds before next attempt...{Colors.RESET}")
                for remaining in range(delay, 0, -1):
                    print(f"\r{Colors.CYAN}Next account in: {Colors.WHITE}{remaining}{Colors.CYAN} seconds{Colors.RESET}", end="")
                    time.sleep(1)
                print("\n")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}Program stopped by user.{Colors.RESET}")

    finally:
        print("\n" + "=" * 70)
        print(f"{Colors.MAGENTA}{Colors.BOLD}SUMMARY:{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Successful accounts: {Colors.WHITE}{creator.success_count}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed accounts: {Colors.WHITE}{creator.fail_count}{Colors.RESET}")
        if proxy_manager:
            print(f"{Colors.CYAN}✓ Working proxies: {Colors.WHITE}{len(proxy_manager.working_proxies)}{Colors.RESET}")
            print(f"{Colors.RED}✗ Failed proxies: {Colors.WHITE}{len(proxy_manager.failed_proxies)}{Colors.RESET}")
        print("=" * 70)

        if creator.success_count > 0 and save_to_file:
            print(f"{Colors.GREEN}Successful accounts saved to instagram_accounts.txt{Colors.RESET}")
            print(f"{Colors.GREEN}Session IDs saved to ACC_SESSIONS_IG.txt{Colors.RESET}")

        print(f"\n{Colors.CYAN}Thank you for using Enhanced Instagram Account Creator!{Colors.RESET}")

if __name__ == "__main__":
    main()