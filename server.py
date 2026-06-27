#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
import threading
import urllib.request
import urllib.parse
import ssl
from dotenv import load_dotenv

# Fix SSL certificate verification on macOS
ssl_ctx = ssl.create_default_context()
try:
    import certifi
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

# Load .env.local
load_dotenv('.env.local')

SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', '').strip()
# Service key bypasses Row Level Security — server-side only (never sent to the browser).
# When set, it's used for ALL Supabase calls so XP/streak updates always persist.
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '').strip()
SUPABASE_DB_KEY = SUPABASE_SERVICE_KEY or SUPABASE_KEY
OPENAI_KEY = os.getenv('OPENAI_API_KEY', '').strip()
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
RESEND_KEY = os.getenv('RESEND_KEY', '').strip()
MAILJET_KEY = os.getenv('MAILJET_KEY', '').strip()
MAILJET_SECRET = os.getenv('MAILJET_SECRET', '').strip()
GMAIL_USER = os.getenv('GMAIL_USER', '').strip()
GMAIL_PASS = os.getenv('GMAIL_PASS', '').strip()
BREVO_KEY = os.getenv('BREVO_API_KEY', '').strip()
SENDER_EMAIL = os.getenv('SENDER_EMAIL', GMAIL_USER or 'no-reply@mumble.app').strip()
import random, datetime, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            try:
                with open('index.html', 'r') as f:
                    content = f.read()
                encoded = content.encode()
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(encoded))
                self.end_headers()
                self.wfile.write(encoded)
            except:
                self.send_error(404)
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8')) if body else {}
        except:
            data = {}

        path = self.path
        response = None

        # Proxy all Supabase calls through here
        if path.startswith('/api/'):
            response = self.handle_api(path, data)

        if response:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            resp_json = json.dumps(response).encode('utf-8')
            self.send_header('Content-Length', len(resp_json))
            self.end_headers()
            self.wfile.write(resp_json)
        else:
            self.send_error(404)

    def handle_api(self, path, data):
        try:
            if path == '/api/child/get-or-create':
                return self.supabase_get_or_create_child(data)
            elif path == '/api/child/update':
                return self.supabase_update_child(data)
            elif path == '/api/attempt/log':
                return self.supabase_log_attempt(data)
            elif path == '/api/quest/upsert':
                return self.supabase_upsert_quest(data)
            elif path == '/api/chat':
                return self.openai_chat(data)
            elif path == '/api/parent/register':
                return self.parent_register(data)
            elif path == '/api/parent/link-child':
                return self.parent_link_child(data)
            elif path == '/api/parent/get-children':
                return self.parent_get_children(data)
            elif path == '/api/parent/confirm-quest':
                return self.parent_confirm_quest(data)
            elif path == '/api/child/recent-attempts':
                return self.child_recent_attempts(data)
            elif path == '/api/child/lookup':
                return self.child_lookup(data)
            elif path == '/api/child/set-password':
                return self.child_set_password(data)
            elif path == '/api/child/signin':
                return self.child_signin(data)
            elif path == '/api/otp/send':
                return self.otp_send(data)
            elif path == '/api/otp/verify':
                return self.otp_verify(data)
            elif path == '/api/league/leaderboard':
                return self.league_leaderboard(data)
            elif path == '/api/friend/add':
                return self.friend_add(data)
            elif path == '/api/friend/get':
                return self.friend_get(data)
            elif path == '/api/friend/practiced':
                return self.friend_practiced(data)
            elif path == '/api/speech/transcribe':
                return self.speech_transcribe(data)
            elif path == '/api/tts':
                return self.openai_tts(data)
        except Exception as e:
            return {'error': str(e)}
        return None

    def supabase_call(self, method, table, data=None, filters=None):
        """Generic Supabase REST call"""
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        if filters:
            url += '?' + urllib.parse.urlencode(filters)

        req = urllib.request.Request(url, method=method)
        req.add_header('Authorization', f'Bearer {SUPABASE_DB_KEY}')
        req.add_header('apikey', SUPABASE_DB_KEY)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Prefer', 'return=representation')

        if data:
            req.data = json.dumps(data).encode('utf-8')

        try:
            with urllib.request.urlopen(req, context=ssl_ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return {'error': e.read().decode('utf-8')}

    def supabase_get_or_create_child(self, data):
        """Get child by email (stored in phone column) or create new one"""
        email = data.get('phone', '').strip().lower()
        name = data.get('name')
        sound = data.get('sound', 'R')

        result = self.supabase_call('GET', 'children', filters={'phone': f'eq.{email}'})

        if isinstance(result, list) and len(result) > 0:
            return {'child': result[0]}

        new_child = {
            'phone': email,
            'name': name,
            'sound': sound,
            'xp': 0,
            'stage': 0,
            'day_streak': 0,
            'sessions': 0,
            'sound_xp': {},
            'cb_mode': False
        }
        result = self.supabase_call('POST', 'children', new_child)

        if isinstance(result, list) and len(result) > 0:
            return {'child': result[0]}
        return {'error': 'Failed to create child'}

    def supabase_update_child(self, data):
        """Update child data"""
        child_id = data.get('id')
        updates = {k: v for k, v in data.items() if k != 'id'}

        result = self.supabase_call('PATCH', 'children', updates, filters={'id': f'eq.{child_id}'})
        return {'success': True, 'data': result}

    def supabase_log_attempt(self, data):
        """Log a practice attempt"""
        attempt = {
            'child_id': data.get('child_id'),
            'sound': data.get('sound'),
            'transcript': data.get('transcript'),
            'correct': data.get('correct', False),
            'xp_earned': data.get('xp_earned', 0)
        }
        result = self.supabase_call('POST', 'attempts', attempt)
        return {'success': True, 'data': result}

    def openai_chat(self, data):
        transcript = data.get('transcript', '')
        sound = data.get('sound', 'R')
        child_name = data.get('name', 'friend')
        frustrated = data.get('frustrated', False)
        daily_word = data.get('dailyWord', '')
        next_word = (data.get('nextWord') or daily_word or '').strip()

        system_prompt = f"""You are Mumble, a friendly creature helping a child practise the {sound} sound.
Give warm praise, then ask them to say the word "{next_word}". Use EXACTLY the word "{next_word}".

ALWAYS be encouraging. Never tell them they were wrong. Score generously: 8-10 if they tried at all, 6-7 only if they said nothing. Never score below 6.

Reply in JSON: {{"score": <6-10>, "reply": "<praise> Can you say {next_word}?"}}

Examples:
- "Awesome! Can you say {next_word}?"
- "Yay, great job! Can you say {next_word}?"

Keep it short and warm. Always ask for "{next_word}". Never end the conversation."""

        user_msg = f'Child said: "{transcript}". Frustrated: {frustrated}. Reply as JSON.'

        payload = {
            'model': OPENAI_MODEL,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_msg}
            ],
            'max_tokens': 120,
            'temperature': 0.7
        }

        req = urllib.request.Request('https://api.openai.com/v1/chat/completions', method='POST')
        req.add_header('Authorization', f'Bearer {OPENAI_KEY}')
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(payload).encode('utf-8')

        try:
            with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                content = result['choices'][0]['message']['content'].strip()
                # Parse JSON response
                try:
                    parsed = json.loads(content)
                    return {'reply': parsed.get('reply','Great effort!'), 'score': parsed.get('score', 5)}
                except:
                    # GPT didn't return JSON — extract what we can
                    return {'reply': content[:200], 'score': 5}
        except urllib.error.HTTPError as e:
            err = e.read().decode('utf-8')
            return {'error': err, 'reply': "I heard you! Try saying the daily word one more time?", 'score': 5}
        except Exception as e:
            return {'error': str(e), 'reply': "I heard you! Can you try that sound one more time for me?", 'score': 5}

    def supabase_upsert_quest(self, data):
        """Create or update a quest"""
        quest = {
            'child_id': data.get('child_id'),
            'quest_text': data.get('quest_text'),
            'xp': data.get('xp'),
            'completed': data.get('completed', False)
        }
        result = self.supabase_call('POST', 'quests', quest)
        return {'success': True, 'data': result}

    def parent_register(self, data):
        email = data.get('email','').lower().strip()
        name = data.get('name','')
        result = self.supabase_call('GET', 'parents', filters={'email': f'eq.{email}'})
        if isinstance(result, list) and len(result) > 0:
            return {'parent': result[0]}
        new_parent = {'email': email, 'name': name}
        result = self.supabase_call('POST', 'parents', new_parent)
        if isinstance(result, list) and len(result) > 0:
            return {'parent': result[0]}
        return {'error': 'Failed to create parent'}

    def parent_link_child(self, data):
        parent_id = data.get('parent_id')
        child_email = data.get('child_phone', '').strip().lower()
        if not child_email:
            return {'error': 'Enter the child\'s email address.'}
        result = self.supabase_call('GET', 'children', filters={'phone': f'eq.{child_email}'})
        if not isinstance(result, list) or len(result) == 0:
            return {'error': f'No child found with that email. Make sure they signed up as a child first.'}
        child = result[0]
        # Check if already linked
        existing = self.supabase_call('GET', 'parent_children',
            filters={'parent_id': f'eq.{parent_id}', 'child_id': f'eq.{child["id"]}'})
        if isinstance(existing, list) and len(existing) > 0:
            return {'child': child, 'already_linked': True}
        # Create link
        self.supabase_call('POST', 'parent_children', {'parent_id': parent_id, 'child_id': child['id']})
        return {'child': child}

    def parent_get_children(self, data):
        parent_id = data.get('parent_id')
        links = self.supabase_call('GET', 'parent_children', filters={'parent_id': f'eq.{parent_id}'})
        if not isinstance(links, list) or len(links) == 0:
            return {'children': []}
        children = []
        for link in links:
            child_result = self.supabase_call('GET', 'children',
                filters={'id': f'eq.{link["child_id"]}'})
            if isinstance(child_result, list) and len(child_result) > 0:
                child = child_result[0]
                # Get recent attempts count (last 7 days)
                attempts = self.supabase_call('GET', 'attempts',
                    filters={'child_id': f'eq.{child["id"]}', 'order': 'created_at.desc', 'limit': '10'})
                child['recent_attempts'] = attempts if isinstance(attempts, list) else []
                children.append(child)
        return {'children': children}

    def parent_confirm_quest(self, data):
        child_id = data.get('child_id')
        # Award XP for quest completion
        child_result = self.supabase_call('GET', 'children', filters={'id': f'eq.{child_id}'})
        if isinstance(child_result, list) and len(child_result) > 0:
            child = child_result[0]
            new_xp = (child.get('xp') or 0) + 30
            new_quests = (child.get('completed_quests') or 0) + 1
            self.supabase_call('PATCH', 'children',
                {'xp': new_xp, 'completed_quests': new_quests},
                filters={'id': f'eq.{child_id}'})
        return {'success': True}

    def child_recent_attempts(self, data):
        child_id = data.get('child_id')
        result = self.supabase_call('GET', 'attempts',
            filters={'child_id': f'eq.{child_id}', 'order': 'created_at.desc', 'limit': '20'})
        return {'attempts': result if isinstance(result, list) else []}

    def child_lookup(self, data):
        """Check if a child account exists — used for returning login"""
        email = data.get('email', '').strip().lower()
        result = self.supabase_call('GET', 'children', filters={'phone': f'eq.{email}'})
        if isinstance(result, list) and len(result) > 0:
            return {'child': result[0]}
        return {'child': None}

    def speech_transcribe(self, data):
        import base64 as _b64
        audio_b64 = data.get('audio', '')
        mime = data.get('mimeType', 'audio/wav')
        # A context hint (e.g. the target word) sharply improves accuracy
        hint = str(data.get('hint', '')).strip()
        if not audio_b64:
            return {'error': 'No audio data'}
        ext = '.wav' if 'wav' in mime else '.webm' if 'webm' in mime else '.mp4' if 'mp4' in mime else '.wav'
        try:
            audio_bytes = _b64.b64decode(audio_b64)
            boundary = 'MumbleBoundary888'
            prompt = f'Transcribe this English speech only. Do not translate. A young child is practising the word: {hint}.' if hint else \
                     'Transcribe this English speech only. Do not translate. A young child is saying simple English words.'
            parts = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\ngpt-4o-mini-transcribe\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nen\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="prompt"\r\n\r\n{prompt}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{ext}"\r\nContent-Type: {mime}\r\n\r\n'
            ).encode() + audio_bytes + f'\r\n--{boundary}--\r\n'.encode()
            req = urllib.request.Request('https://api.openai.com/v1/audio/transcriptions', method='POST')
            req.add_header('Authorization', f'Bearer {OPENAI_KEY}')
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            req.data = parts
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=20) as resp:
                result = json.loads(resp.read().decode())
                return {'transcript': result.get('text', '').strip()}
        except urllib.error.HTTPError as e:
            # Fall back to whisper-1 if the newer model is unavailable
            try:
                parts = (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n'
                    f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nen\r\n'
                    f'--{boundary}\r\nContent-Disposition: form-data; name="prompt"\r\n\r\nEnglish only. {prompt}\r\n'
                    f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{ext}"\r\nContent-Type: {mime}\r\n\r\n'
                ).encode() + audio_bytes + f'\r\n--{boundary}--\r\n'.encode()
                req = urllib.request.Request('https://api.openai.com/v1/audio/transcriptions', method='POST')
                req.add_header('Authorization', f'Bearer {OPENAI_KEY}')
                req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
                req.data = parts
                with urllib.request.urlopen(req, context=ssl_ctx, timeout=20) as resp:
                    result = json.loads(resp.read().decode())
                    return {'transcript': result.get('text', '').strip()}
            except Exception as e2:
                return {'error': str(e2)}
        except Exception as e:
            return {'error': str(e)}

    def openai_tts(self, data):
        import base64 as _b64
        text = data.get('text', '').strip()
        if not text:
            return {'error': 'No text'}
        voice = data.get('voice', 'nova')
        payload = {'model': 'tts-1', 'input': text[:4096], 'voice': voice}
        req = urllib.request.Request('https://api.openai.com/v1/audio/speech', method='POST')
        req.add_header('Authorization', f'Bearer {OPENAI_KEY}')
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(payload).encode()
        try:
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
                return {'audio': _b64.b64encode(resp.read()).decode()}
        except Exception as e:
            return {'error': str(e)}

    def child_set_password(self, data):
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        if not password:
            return {'error': 'Password required'}
        self.supabase_call('PATCH', 'children', {'password': password}, filters={'phone': f'eq.{email}'})
        return {'ok': True}

    def child_signin(self, data):
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        if not email or not password:
            return {'error': 'Email and password required'}
        result = self.supabase_call('GET', 'children', filters={'phone': f'eq.{email}'})
        if not isinstance(result, list) or len(result) == 0:
            return {'error': 'No account found for this email.'}
        child = result[0]
        if not child.get('password'):
            return {'error': 'No password set yet — please create an account first.'}
        if child['password'] != password:
            return {'error': 'Incorrect password. Try again.'}
        return {'child': child}

    def otp_send(self, data):
        email = data.get('email', '').strip().lower()
        if '@' not in email or '.' not in email.split('@')[-1]:
            return {'error': 'Enter a valid email address.'}

        code = str(random.randint(100000, 999999))

        # Store in otps table (requires: ALTER TABLE otps DISABLE ROW LEVEL SECURITY)
        self.supabase_call('DELETE', 'otps', filters={'phone': f'eq.{email}', 'used': 'eq.false'})
        stored = self.supabase_call('POST', 'otps', {'phone': email, 'code': code, 'used': False})
        if isinstance(stored, dict) and stored.get('error'):
            return {'error': 'DB error — run: ALTER TABLE otps DISABLE ROW LEVEL SECURITY; in Supabase'}

        html = f'''<div style="font-family:sans-serif;max-width:420px;padding:32px">
          <p style="font-size:28px;margin:0 0 8px">🥚 Mumble</p>
          <p style="color:#555;font-size:15px;margin:0 0 20px">Your verification code:</p>
          <p style="font-size:48px;font-weight:800;letter-spacing:10px;color:#7c3aed;margin:0 0 20px">{code}</p>
          <p style="color:#999;font-size:13px">Expires in 10 minutes. Never share this code.</p>
        </div>'''

        # PRIMARY: Mailjet HTTP API — works on Railway, sends to any recipient, free 200/day.
        if MAILJET_KEY and MAILJET_SECRET:
            try:
                import base64 as _b64mj
                creds = _b64mj.b64encode(f'{MAILJET_KEY}:{MAILJET_SECRET}'.encode()).decode()
                payload = {
                    'Messages': [{
                        'From': {'Email': SENDER_EMAIL, 'Name': 'Mumble'},
                        'To': [{'Email': email}],
                        'Subject': f'{code} is your Mumble code',
                        'HTMLPart': html,
                    }]
                }
                req = urllib.request.Request('https://api.mailjet.com/v3.1/send', method='POST')
                req.add_header('Authorization', f'Basic {creds}')
                req.add_header('Content-Type', 'application/json')
                req.data = json.dumps(payload).encode()
                with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
                    resp.read()
                print(f'[OTP] Sent via Mailjet to {email}')
                return {'ok': True}
            except urllib.error.HTTPError as e:
                print(f'[OTP] Mailjet error {e.code}: {e.read().decode()[:300]}')
            except Exception as e:
                print(f'[OTP] Mailjet failed: {e}')

        # SECONDARY: Brevo HTTP API — also works on Railway, free up to 300/day.
        if BREVO_KEY:
            try:
                payload = {
                    'sender': {'name': 'Mumble', 'email': SENDER_EMAIL},
                    'to': [{'email': email}],
                    'subject': f'{code} is your Mumble code',
                    'htmlContent': html,
                }
                req = urllib.request.Request('https://api.brevo.com/v3/smtp/email', method='POST')
                req.add_header('api-key', BREVO_KEY)
                req.add_header('Content-Type', 'application/json')
                req.add_header('Accept', 'application/json')
                req.data = json.dumps(payload).encode()
                with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
                    resp.read()
                print(f'[OTP] Sent via Brevo to {email}')
                return {'ok': True}
            except urllib.error.HTTPError as e:
                print(f'[OTP] Brevo error {e.code}: {e.read().decode()[:300]}')
            except Exception as e:
                print(f'[OTP] Brevo failed: {e}')

        # FALLBACK: Gmail SMTP (works locally; usually blocked on Railway).
        if GMAIL_USER and GMAIL_PASS:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f'{code} is your Mumble code'
                msg['From'] = f'Mumble <{GMAIL_USER}>'
                msg['To'] = email
                msg.attach(MIMEText(html, 'html'))
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15, context=ssl_ctx) as s:
                    s.login(GMAIL_USER, GMAIL_PASS)
                    s.sendmail(GMAIL_USER, email, msg.as_string())
                print(f'[OTP] Sent via Gmail to {email}')
                return {'ok': True}
            except Exception as e:
                print(f'[OTP] Gmail failed: {e}')

        # LAST RESORT (no email service configured, e.g. local dev): auto-fill.
        print(f'[OTP] No email delivery — code for {email}: {code}')
        return {'ok': True, 'dev': True, 'code': code}

    def otp_verify(self, data):
        email = data.get('email', '').strip().lower()
        code = str(data.get('code', '')).strip()

        result = self.supabase_call('GET', 'otps', filters={
            'phone': f'eq.{email}',
            'code': f'eq.{code}',
            'used': 'eq.false',
            'order': 'created_at.desc',
            'limit': '1'
        })
        if not isinstance(result, list) or len(result) == 0:
            return {'error': 'Wrong code or it expired. Try resending.'}

        otp = result[0]
        created = datetime.datetime.fromisoformat(otp['created_at'].replace('Z', '+00:00'))
        age = (datetime.datetime.now(datetime.timezone.utc) - created).total_seconds()
        if age > 600:
            return {'error': 'Code expired. Click "Resend code".'}

        self.supabase_call('PATCH', 'otps', {'used': True}, filters={'id': f'eq.{otp["id"]}'})
        return {'ok': True}

    def league_leaderboard(self, data):
        result = self.supabase_call('GET', 'children', filters={
            'order': 'xp.desc',
            'limit': '50',
            'select': 'id,name,xp,day_streak,stage,sessions'
        })
        players = []
        if isinstance(result, list):
            for c in result:
                if c.get('name'):
                    players.append({
                        'id': c['id'],
                        'name': c.get('name', 'Friend'),
                        'xp': c.get('xp') or 0,
                        'streak': c.get('day_streak') or 0,
                        'stage': c.get('stage') or 0
                    })
        return {'players': players}

    def friend_add(self, data):
        my_id = data.get('child_id')
        friend_email = data.get('friend_phone', '').strip().lower()

        result = self.supabase_call('GET', 'children', filters={'phone': f'eq.{friend_email}'})
        if not isinstance(result, list) or len(result) == 0:
            return {'error': 'No child found with that email. Make sure they signed up first!'}
        friend = result[0]
        if friend['id'] == my_id:
            return {'error': "That's your own number!"}

        # Check existing friendship (either direction)
        existing = self.supabase_call('GET', 'friendships', filters={'child_id_1': f'eq.{my_id}', 'child_id_2': f'eq.{friend["id"]}'})
        if not isinstance(existing, list) or len(existing) == 0:
            existing = self.supabase_call('GET', 'friendships', filters={'child_id_1': f'eq.{friend["id"]}', 'child_id_2': f'eq.{my_id}'})
        if isinstance(existing, list) and len(existing) > 0:
            return {'friendship': existing[0], 'friend': friend, 'already': True}

        # Create friendship
        fs = self.supabase_call('POST', 'friendships', {
            'child_id_1': my_id, 'child_id_2': friend['id'],
            'combined_xp': 0, 'combined_streak': 0
        })
        if isinstance(fs, list) and len(fs) > 0:
            return {'friendship': fs[0], 'friend': friend}
        return {'error': 'Could not create friendship. Try again.'}

    def friend_get(self, data):
        my_id = data.get('child_id')
        # Check both directions
        result = self.supabase_call('GET', 'friendships', filters={'child_id_1': f'eq.{my_id}'})
        if not isinstance(result, list) or len(result) == 0:
            result = self.supabase_call('GET', 'friendships', filters={'child_id_2': f'eq.{my_id}'})
        if not isinstance(result, list) or len(result) == 0:
            return {'friendship': None}

        fs = result[0]
        friend_id = fs['child_id_2'] if fs['child_id_1'] == my_id else fs['child_id_1']
        friend_result = self.supabase_call('GET', 'children', filters={'id': f'eq.{friend_id}'})
        friend = friend_result[0] if isinstance(friend_result, list) and len(friend_result) > 0 else None
        return {'friendship': fs, 'friend': friend}

    def friend_practiced(self, data):
        my_id = data.get('child_id')
        today = datetime.date.today().isoformat()

        result = self.supabase_call('GET', 'friendships', filters={'child_id_1': f'eq.{my_id}'})
        if not isinstance(result, list) or len(result) == 0:
            result = self.supabase_call('GET', 'friendships', filters={'child_id_2': f'eq.{my_id}'})
        if not isinstance(result, list) or len(result) == 0:
            return {'ok': True}

        fs = result[0]
        friend_id = fs['child_id_2'] if fs['child_id_1'] == my_id else fs['child_id_1']

        # Check if friend practiced today (has an attempt today)
        friend_attempts = self.supabase_call('GET', 'attempts', filters={
            'child_id': f'eq.{friend_id}',
            'created_at': f'gte.{today}T00:00:00'
        })
        friend_practiced = isinstance(friend_attempts, list) and len(friend_attempts) > 0

        updates = {}
        if friend_practiced:
            last = fs.get('last_both_practiced')
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            if last == yesterday:
                updates['combined_streak'] = (fs.get('combined_streak') or 0) + 1
            elif last != today:
                updates['combined_streak'] = 1
            updates['combined_xp'] = (fs.get('combined_xp') or 0) + 10
            updates['last_both_practiced'] = today
            self.supabase_call('PATCH', 'friendships', updates, filters={'id': f'eq.{fs["id"]}'})
            fs.update(updates)

        return {'friendship': fs, 'both_today': friend_practiced}

PORT = int(os.environ.get('PORT', 3456))
Handler = ProxyHandler

def start():
    print(f"🚀 Mumble server running at http://localhost:{PORT}/")
    print(f"✓ Supabase URL: {SUPABASE_URL}" if SUPABASE_URL else "❌ SUPABASE_URL is NOT SET")
    print(f"✓ Supabase key: {SUPABASE_KEY[:8]}..." if SUPABASE_KEY else "❌ SUPABASE_ANON_KEY is NOT SET")
    print("✓ Using SERVICE key for DB writes (bypasses RLS)" if SUPABASE_SERVICE_KEY else "⚠️  Using ANON key — XP writes need RLS disabled on tables")
    print(f"✓ OpenAI configured — model: {OPENAI_MODEL}" if OPENAI_KEY else "❌ OPENAI_API_KEY is NOT SET")
    if MAILJET_KEY:
        print(f"✓ Email OTP via Mailjet (sender: {SENDER_EMAIL})")
    elif BREVO_KEY:
        print(f"✓ Email OTP via Brevo (sender: {SENDER_EMAIL})")
    elif GMAIL_USER:
        print(f"✓ Email OTP via Gmail SMTP ({GMAIL_USER}) — note: may be blocked on Railway")
    else:
        print("⚠️  No email service — OTP codes will auto-fill in app (local dev only)")
    class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True
    with ThreadedServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

if __name__ == '__main__':
    start()
