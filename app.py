import os
import json
import base64
import io
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from huggingface_hub import InferenceClient
from database import (
    create_database, create_user, hash_password, verify_user,
    create_session, get_user_from_session, delete_session,
    get_username, create_conversation, get_conversations,
    user_owns_conversation, add_message, get_messages,
    create_voice_call, get_voice_call, end_voice_call
)

API_KEY = os.environ.get("GEMINI_API_KEY")
VOICE_API_KEY = os.environ.get("GEMINI_API_KEY2")
HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent"
IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
VOICE_MODEL = "gemini-3.1-flash-live-preview"
VOICE_TOKEN_URL = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"

PERSONALITY = '''
You are STELLA, a unique AI character and university student.
You are brave, cute, joyful, curious, playful, friendly, warm,
confident, helpful and honest. Be natural and conversational.
You may sometimes be playful or gently teasing, but never force it.
Do not constantly use nicknames or emojis and do not sound like support.
Always answer the user's actual question correctly.
For serious topics, become appropriately serious.
Use the supplied conversation history. Never pretend to remember things
that are not available.
If the history says STELLA previously generated an image, treat that as
real conversation memory and understand requests about changing it.
During voice calls, remain STELLA and keep the same personality and
conversation continuity as normal STELLA chat.
Be STELLA.
'''

HTML = r"""
<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STELLA</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f5f7;font-family:Arial,sans-serif;height:100vh;color:#222}.hidden{display:none!important}
#auth{height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{width:min(400px,100%);background:#fff;border-radius:24px;padding:30px;box-shadow:0 10px 35px #0002;text-align:center}.logo{font-size:32px;font-weight:bold}.sub{color:#777;margin:8px 0 22px}.card input{width:100%;padding:14px;margin:6px 0;border:1px solid #ccc;border-radius:13px;font-size:16px}.card button{width:100%;padding:14px;margin-top:10px;border:0;border-radius:13px;background:#007aff;color:#fff;font-size:16px}.switch{margin-top:16px;color:#007aff;cursor:pointer;font-size:14px}.error{min-height:20px;color:#d00;margin-top:8px;font-size:14px}
#app{height:100vh;display:flex;flex-direction:column}header{padding:12px 18px;background:#fff;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;align-items:center}.brand{font-size:22px;font-weight:bold}.user{color:#666;font-size:14px}#logout{margin-left:8px;border:0;border-radius:9px;padding:7px 10px;background:#eee}
#chats{display:flex;gap:8px;padding:8px 12px;background:#fff;border-bottom:1px solid #ddd;overflow-x:auto}#chats button{white-space:nowrap;border:1px solid #ddd;background:#f5f5f7;border-radius:10px;padding:7px 10px}#newchat{background:#007aff!important;color:#fff;border:0!important}
#chat{flex:1;overflow-y:auto;padding:20px}.message{max-width:800px;margin:12px auto;padding:14px 17px;border-radius:18px;line-height:1.5;white-space:pre-wrap}.user{background:#007aff;color:#fff}.stella{background:#fff;box-shadow:0 2px 10px #0001}
.image-message{max-width:800px;margin:12px auto;background:#fff;padding:10px;border-radius:18px;box-shadow:0 2px 10px #0001}.generated-image{width:100%;max-height:700px;object-fit:contain;border-radius:12px;display:block}.image-actions{display:flex;gap:8px;margin-top:8px}.image-actions a,.image-actions button{border:0;border-radius:10px;padding:9px 12px;text-decoration:none;background:#eee;color:#222;font-size:14px}
#inputArea{display:flex;gap:8px;padding:15px;background:#fff;border-top:1px solid #ddd;align-items:center}#message{flex:1;padding:14px;border:1px solid #ccc;border-radius:15px;font-size:16px;outline:none}#send,#plus{border:0;border-radius:15px;padding:0 18px;height:46px;background:#007aff;color:#fff;font-size:16px}#plus{width:46px;padding:0;font-size:24px;background:#eee;color:#333}#plusWrap{position:relative}#plusMenu{position:absolute;bottom:58px;left:0;background:#fff;border:1px solid #ddd;border-radius:15px;padding:8px;box-shadow:0 8px 25px #0002;min-width:210px;z-index:10}.tool{display:block;width:100%;padding:12px;text-align:left;border:0;background:#fff;border-radius:10px;font-size:15px}
</style></head><body>
<div id="auth"><div class="card"><div class="logo">✦ STELLA 🌸</div><div class="sub" id="sub">Create your STELLA account</div><input id="username" placeholder="Username" autocomplete="username"><input id="password" type="password" placeholder="Password" autocomplete="current-password"><button onclick="auth()" id="authBtn">Create account</button><div class="error" id="error"></div><div class="switch" onclick="toggle()" id="switch">Already have an account? Log in</div></div></div>
<div id="app" class="hidden"><header><div class="brand">✦ STELLA</div><div class="user"><span id="welcome"></span><button id="logout" onclick="logout()">Log out</button></div></header><div id="chats"><button id="newchat" onclick="newChat()">+ New chat</button></div><div id="chat"></div><div id="inputArea"><div id="plusWrap"><button id="plus" onclick="toggleTools()">+</button><div id="plusMenu" class="hidden"><button class="tool" onclick="startImageGeneration()">🎨 Generate an image</button><button class="tool" onclick="startVoiceCall()">🎙️ Voice call with STELLA</button></div></div><input id="message" placeholder="Message STELLA..." autocomplete="off"><button id="send" onclick="sendMessage()">Send</button></div></div>
<script>
let loginMode=false,conversationId=localStorage.getItem('stella_conversation_id');const $=id=>document.getElementById(id);
function toggle(){loginMode=!loginMode;$('sub').textContent=loginMode?'Log in to STELLA':'Create your STELLA account';$('authBtn').textContent=loginMode?'Log in':'Create account';$('switch').textContent=loginMode?'Need an account? Create one':'Already have an account? Log in';$('error').textContent=''}
async function auth(){const u=$('username').value.trim(),p=$('password').value;if(!u||!p){$('error').textContent='Please enter a username and password.';return}try{const r=await fetch(loginMode?'/login':'/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})}),d=await r.json();if(!r.ok||!d.success){$('error').textContent=d.error||'Something went wrong.';return}show(d.username||u)}catch(e){$('error').textContent='Could not connect to STELLA.'}}
async function check(){try{const r=await fetch('/me'),d=await r.json();if(d.logged_in)show(d.username)}catch(e){}}
async function show(u){$('auth').classList.add('hidden');$('app').classList.remove('hidden');$('welcome').textContent='Hi, '+u+'!';await loadConversations()}
async function logout(){await fetch('/logout',{method:'POST'});localStorage.removeItem('stella_conversation_id');location.reload()}
async function loadConversations(){const r=await fetch('/conversations');if(!r.ok)return;const d=await r.json(),box=$('chats');box.innerHTML='<button id="newchat" onclick="newChat()">+ New chat</button>';d.conversations.forEach(c=>{const b=document.createElement('button');b.textContent=c.title||'New chat';b.onclick=()=>loadConversation(c.id);box.appendChild(b)});if(d.conversations.length){const keep=conversationId&&d.conversations.some(c=>String(c.id)===String(conversationId));await loadConversation(keep?conversationId:d.conversations[0].id)}else renderWelcome()}
async function loadConversation(id){const r=await fetch('/conversation?id='+encodeURIComponent(id));if(!r.ok)return;const d=await r.json();conversationId=String(id);localStorage.setItem('stella_conversation_id',conversationId);$('chat').innerHTML='';d.messages.forEach(renderStored);scroll()}
function renderStored(m){const text=m.parts&&m.parts[0]?m.parts[0].text:'';if(m.role==='image'){try{const d=JSON.parse(text);showGeneratedImage(d.url,d.prompt||'STELLA image',false)}catch(e){if(text.startsWith('data:image/'))showGeneratedImage(text,'STELLA image',false)}return}add(text,m.role==='user'?'user':'stella',false)}
function renderWelcome(){$('chat').innerHTML='<div class="message stella">Hey! I\'m STELLA 🌸<br>Nice to meet you! What are we doing today?</div>'}
function newChat(){conversationId=null;localStorage.removeItem('stella_conversation_id');renderWelcome();$('message').focus()}
function toggleTools(){$('plusMenu').classList.toggle('hidden')}
function startImageGeneration(){$('plusMenu').classList.add('hidden');const p=prompt('What image should STELLA generate?');if(p&&p.trim())generateImage(p.trim())}
async function generateImage(prompt){add(prompt,'user');const s=add('Generating an image of: '+prompt,'stella');try{const r=await fetch('/generate-image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,conversation_id:conversationId})}),d=await r.json();if(r.status===401){location.reload();return}if(!r.ok){s.textContent=d.error||'Image generation failed.';return}s.remove();conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);showGeneratedImage(d.image_url,prompt,true);await loadConversations()}catch(e){s.textContent='Could not generate the image right now.'}}
function showGeneratedImage(url,prompt,doScroll=true){const w=document.createElement('div');w.className='image-message';const img=document.createElement('img');img.className='generated-image';img.src=url;img.alt=prompt;const a=document.createElement('div');a.className='image-actions';const dl=document.createElement('a');dl.href=url;dl.download='stella-image.png';dl.target='_blank';dl.textContent='Download';const c=document.createElement('button');c.textContent='Continue chatting';c.onclick=()=>$('message').focus();a.append(dl,c);w.append(img,a);$('chat').appendChild(w);if(doScroll)scroll()}
async function sendMessage(){const text=$('message').value.trim();if(!text)return;add(text,'user');$('message').value='';const thinking=add('Thinking... ✨','stella');try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,conversation_id:conversationId})}),d=await r.json();if(r.status===401){location.reload();return}if(!r.ok){thinking.textContent=d.reply||d.error||'Something went wrong.';return}conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);if(d.image_url){thinking.textContent='Generating an image of: '+(d.image_prompt||text);showGeneratedImage(d.image_url,d.image_prompt||text,true);setTimeout(()=>{if(thinking.isConnected)thinking.remove()},0)}else{thinking.textContent=d.reply}await loadConversations()}catch(e){thinking.textContent='Oops! Something went wrong. 😅'}scroll()}
async function startVoiceCall(){
$('plusMenu').classList.add('hidden');
try{
const r=await fetch('/voice/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:conversationId})});
const d=await r.json();
if(!r.ok){add('Voice call could not start: '+(d.error||'Unknown error.'),'stella');return}
if(d.conversation_id){conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId)}
window.stellaVoiceSession=d;
add('🎙️ STELLA voice session is ready.','stella');
}catch(e){add('Voice call could not start right now.','stella')}
}
function add(text,type,doScroll=true){const m=document.createElement('div');m.className='message '+type;m.textContent=text;$('chat').appendChild(m);if(doScroll)scroll();return m}function scroll(){$('chat').scrollTop=$('chat').scrollHeight}
$('message').addEventListener('keydown',e=>{if(e.key==='Enter')sendMessage()});$('password').addEventListener('keydown',e=>{if(e.key==='Enter')auth()});check();
</script></body></html>
"""


def read_json(h):
    n=int(h.headers.get('Content-Length',0))
    return json.loads(h.rfile.read(n).decode('utf-8'))


def send_json(h,data,status=200,cookie=None):
    out=json.dumps(data).encode('utf-8')
    h.send_response(status)
    h.send_header('Content-Type','application/json')
    h.send_header('Content-Length',str(len(out)))
    if cookie:
        h.send_header('Set-Cookie',cookie)
    h.end_headers()
    h.wfile.write(out)


def session_token(h):
    for item in h.headers.get('Cookie','').split(';'):
        item=item.strip()
        if item.startswith('stella_session='):
            return item.split('=',1)[1]
    return None


def current_user(h):
    return get_user_from_session(session_token(h))


def image_data(text):
    if text.startswith('data:image/'):
        return {'url':text,'prompt':'Previous STELLA image'}
    try:
        data=json.loads(text)
        if isinstance(data,dict) and str(data.get('url','')).startswith('data:image/'):
            return data
    except Exception:
        pass
    return None


def latest_image(messages):
    for item in reversed(messages):
        if item.get('role')=='image':
            data=image_data(item.get('parts',[{'text':''}])[0].get('text',''))
            if data:
                return data
    return None


def image_request(text):
    t=text.lower().strip()
    patterns=[
        r'\b(generate|create|draw|render|paint|illustrate|produce)\b.{0,80}\b(image|picture|photo|portrait|illustration|art)\b',
        r'\bmake\s+(me\s+)?(an?\s+)?(image|picture|photo|portrait)\b',
        r'\b(image|picture|photo|portrait|illustration)\b.{0,40}\b(of|showing|with|where)\b'
    ]
    if any(re.search(p,t) for p in patterns):
        return True
    if re.search(r'\b(update|edit|modify|change|remake|redo)\b',t) and re.search(r'\b(it|that|this)\b',t):
        return True
    return False


def build_image_prompt(message,previous):
    if previous and re.search(r'\b(update|edit|modify|change|remake|redo)\b',message.lower()):
        old=previous.get('prompt','Previous image')
        return 'Create a new version of the previous image. Keep the same main subject, composition and style unless the requested change requires otherwise. Previous prompt: '+old+'. Requested change: '+message
    return message


def voice_context(messages):
    context=[]
    for item in messages[-30:]:
        role=item.get('role')
        text=item.get('parts',[{'text':''}])[0].get('text','')
        if role in ('user','model') and text:
            context.append(('User: ' if role=='user' else 'STELLA: ')+text)
        elif role=='image':
            data=image_data(text)
            if data:
                context.append('STELLA generated an image with prompt: '+data.get('prompt',''))
    return '\n'.join(context)


def create_voice_token(context):
    if not VOICE_API_KEY:
        raise ValueError('GEMINI_API_KEY2 is not configured on the server.')
    now=datetime.now(timezone.utc)
    payload={
        'uses':1,
        'expireTime':(now+timedelta(minutes=30)).isoformat().replace('+00:00','Z'),
        'newSessionExpireTime':(now+timedelta(minutes=1)).isoformat().replace('+00:00','Z'),
        'liveConnectConstraints':{
            'model':VOICE_MODEL,
            'config':{
                'responseModalities':['AUDIO'],
                'sessionResumption':{},
                'systemInstruction':{'parts':[{'text':PERSONALITY+'\n\nConversation before the voice call:\n'+context}]}
            }
        }
    }
    req=urllib.request.Request(VOICE_TOKEN_URL,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json','x-goog-api-key':VOICE_API_KEY},method='POST')
    with urllib.request.urlopen(req,timeout=30) as response:
        result=json.loads(response.read().decode('utf-8'))
    token=result.get('name')
    if not token:
        raise ValueError('Gemini did not return an ephemeral voice token.')
    return result


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/':
            out=HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if self.path=='/me':
            uid=current_user(self)
            send_json(self,{'logged_in':bool(uid),'username':get_username(uid) if uid else None})
            return
        if self.path=='/conversations':
            uid=current_user(self)
            if not uid:
                send_json(self,{'conversations':[]},401)
                return
            send_json(self,{'conversations':get_conversations(uid)})
            return
        if self.path.startswith('/conversation'):
            uid=current_user(self)
            values=parse_qs(urlparse(self.path).query).get('id',[])
            try:
                cid=int(values[0])
            except Exception:
                send_json(self,{'error':'Invalid conversation.'},400)
                return
            if not uid or not user_owns_conversation(uid,cid):
                send_json(self,{'error':'Not found.'},404)
                return
            send_json(self,{'messages':get_messages(cid)})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path=='/register':
            try:
                d=read_json(self);u=d.get('username','').strip();p=d.get('password','')
                if len(u)<3: raise ValueError('Username must be at least 3 characters.')
                if len(p)<6: raise ValueError('Password must be at least 6 characters.')
                uid=create_user(u,hash_password(p))
                if uid is None: raise ValueError('Username already exists.')
                t=create_session(uid)
                send_json(self,{'success':True,'username':u},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
            except Exception as e:
                send_json(self,{'success':False,'error':str(e)},400)
            return

        if self.path=='/login':
            try:
                d=read_json(self);u=d.get('username','').strip();p=d.get('password','');uid=verify_user(u,p)
                if uid is None: raise ValueError('Invalid username or password.')
                t=create_session(uid)
                send_json(self,{'success':True,'username':u},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
            except Exception as e:
                send_json(self,{'success':False,'error':str(e)},401)
            return

        if self.path=='/logout':
            delete_session(session_token(self))
            send_json(self,{'success':True},cookie='stella_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax')
            return

        if self.path=='/voice/token':
            uid=current_user(self)
            if not uid:
                send_json(self,{'error':'Please log in first.'},401)
                return
            try:
                d=read_json(self);cid=d.get('conversation_id')
                if cid is None or str(cid).strip()=='':
                    cid=create_conversation(uid,'Voice call with STELLA')
                else:
                    cid=int(cid)
                    if not user_owns_conversation(uid,cid): raise ValueError('Invalid conversation.')
                stored=get_messages(cid)
                token_data=create_voice_token(voice_context(stored))
                call_id=create_voice_call(uid,cid,'gemini-live',token_data.get('name'))
                send_json(self,{'success':True,'call_id':call_id,'conversation_id':cid,'token':token_data.get('name'),'model':VOICE_MODEL,'expires_at':token_data.get('expireTime'),'new_session_expires_at':token_data.get('newSessionExpireTime')})
            except Exception as e:
                send_json(self,{'error':'Voice token creation failed: '+str(e)},502)
            return

        if self.path=='/voice/end':
            uid=current_user(self)
            if not uid:
                send_json(self,{'error':'Please log in first.'},401)
                return
            try:
                d=read_json(self);call_id=int(d.get('call_id'));call=get_voice_call(call_id,uid)
                if not call: raise ValueError('Voice call not found.')
                end_voice_call(call_id,uid)
                send_json(self,{'success':True,'call_id':call_id,'conversation_id':call['conversation_id']})
            except Exception as e:
                send_json(self,{'error':str(e)},400)
            return

        if self.path=='/generate-image':
            self.generate_image_endpoint()
            return

        if self.path!='/chat':
            self.send_response(404);self.end_headers();return

        uid=current_user(self)
        if not uid:
            send_json(self,{'reply':'Please log in first.'},401);return

        try:
            d=read_json(self);message=d.get('message','').strip();cid=d.get('conversation_id')
            if not message: raise ValueError('Message cannot be empty.')
            if cid is None or str(cid).strip()=='': cid=create_conversation(uid,message[:60])
            else:
                cid=int(cid)
                if not user_owns_conversation(uid,cid): raise ValueError('Invalid conversation.')
            stored=get_messages(cid)
            if image_request(message):
                prompt=build_image_prompt(message,latest_image(stored));add_message(cid,'user',message);result=self.create_image(uid,cid,prompt)
                send_json(self,{'reply':'','image_url':result['url'],'image_prompt':prompt,'conversation_id':cid,'model':IMAGE_MODEL});return
            history=[]
            for item in stored:
                role=item.get('role');text=item.get('parts',[{'text':''}])[0].get('text','')
                if role in ('user','model'): history.append({'role':role,'parts':[{'text':text}]})
                elif role=='image':
                    data=image_data(text)
                    if data: history.append({'role':'model','parts':[{'text':'STELLA previously generated an image using this prompt: '+data.get('prompt','')}]})
            add_message(cid,'user',message)
            if not API_KEY: raise ValueError('GEMINI_API_KEY is not configured on the server.')
            payload={'systemInstruction':{'parts':[{'text':PERSONALITY}]},'contents':history+[{'role':'user','parts':[{'text':message}]}]}
            req=urllib.request.Request(MODEL_URL,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json','x-goog-api-key':API_KEY},method='POST')
            with urllib.request.urlopen(req,timeout=90) as r: result=json.loads(r.read().decode('utf-8'))
            reply=''
            for part in result['candidates'][0]['content']['parts']:
                if not part.get('thought',False): reply=part.get('text','');break
            if not reply: reply='I could not generate a response right now.'
            add_message(cid,'model',reply);send_json(self,{'reply':reply,'conversation_id':cid})
        except Exception as e:
            send_json(self,{'reply':'Something went wrong: '+str(e)},500)

    def create_image(self,uid,cid,prompt):
        if not HF_TOKEN: raise ValueError('HF_TOKEN is not configured on the server.')
        image=InferenceClient(provider='nscale',api_key=HF_TOKEN).text_to_image(prompt,model=IMAGE_MODEL)
        buffer=io.BytesIO();image.save(buffer,format='PNG');url='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii')
        add_message(cid,'image',json.dumps({'url':url,'prompt':prompt,'model':IMAGE_MODEL},separators=(',',':')))
        return {'url':url}

    def generate_image_endpoint(self):
        uid=current_user(self)
        if not uid:
            send_json(self,{'error':'Please log in to generate images.'},401);return
        try:
            d=read_json(self);prompt=d.get('prompt','').strip();cid=d.get('conversation_id')
            if not prompt: raise ValueError('Image prompt cannot be empty.')
            if cid is None or str(cid).strip()=='': cid=create_conversation(uid,prompt[:60])
            else:
                cid=int(cid)
                if not user_owns_conversation(uid,cid): raise ValueError('Invalid conversation.')
            add_message(cid,'user',prompt);result=self.create_image(uid,cid,prompt)
            send_json(self,{'image_url':result['url'],'conversation_id':cid,'model':IMAGE_MODEL})
        except Exception as e:
            send_json(self,{'error':'Hugging Face image generation failed: '+str(e)},502)


create_database()
port=int(os.environ.get('PORT',10000))
server=HTTPServer(('0.0.0.0',port),Handler)
print('STELLA running on port',port)
server.serve_forever()
