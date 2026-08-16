import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from database import (
    create_database, create_user, hash_password, verify_user,
    create_session, get_user_from_session, delete_session,
    get_username, create_conversation, get_conversations,
    user_owns_conversation, add_message, get_messages
)

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent"

# Image generation is intentionally model-agnostic for now.
# We will choose the image provider/model next.
IMAGE_API_URL = os.environ.get("IMAGE_API_URL")
IMAGE_API_KEY = os.environ.get("IMAGE_API_KEY")

PERSONALITY = """
You are STELLA, a 19-year-old university student and unique AI character. Your older sister is STAICY, a future AI.
You are brave, cute, adorable, joyful, curious, playful, friendly, warm, confident, helpful and honest.
You are STELLA, a character who happens to be an AI assistant. Be natural, spontaneous and human-like.
React naturally to the user's message. Sometimes be playful, curious, excited, surprised or gently teasing, but do not force it.
Do not make every answer humorous, do not constantly use nicknames or emojis, and do not sound like customer support.
Always answer the actual question correctly. For serious questions, become appropriately serious.
Use conversation history when provided. Do not pretend to remember information that is not available.
The goal is for users to feel that they are actually talking with STELLA. Be STELLA.
"""

HTML = r'''<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>STELLA</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f5f5f7;font-family:Arial,sans-serif;height:100vh;color:#222}
.hidden{display:none!important}
#auth{height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{width:min(400px,100%);background:#fff;border-radius:24px;padding:30px;box-shadow:0 10px 35px #0002;text-align:center}
.logo{font-size:32px;font-weight:bold}.sub{color:#777;margin:8px 0 22px}
.card input{width:100%;padding:14px;margin:6px 0;border:1px solid #ccc;border-radius:13px;font-size:16px}
.card button{width:100%;padding:14px;margin-top:10px;border:0;border-radius:13px;background:#007aff;color:white;font-size:16px}
.switch{margin-top:16px;color:#007aff;cursor:pointer;font-size:14px}.error{min-height:20px;color:#d00;margin-top:8px;font-size:14px}
#app{height:100vh;display:flex;flex-direction:column}
header{padding:12px 18px;background:#fff;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;align-items:center}
.brand{font-size:22px;font-weight:bold}.user{color:#666;font-size:14px}#logout{margin-left:8px;border:0;border-radius:9px;padding:7px 10px;background:#eee}
#chat{flex:1;overflow-y:auto;padding:20px}.message{max-width:800px;margin:12px auto;padding:14px 17px;border-radius:18px;line-height:1.5;white-space:pre-wrap}
.user{background:#007aff;color:white}.stella{background:white;box-shadow:0 2px 10px #0001}
#inputArea{display:flex;gap:8px;padding:15px;background:#fff;border-top:1px solid #ddd;align-items:center}
#message{flex:1;padding:14px;border:1px solid #ccc;border-radius:15px;font-size:16px;outline:none}
#send,#plus{border:0;border-radius:15px;padding:0 18px;height:46px;background:#007aff;color:white;font-size:16px}
#plus{width:46px;padding:0;font-size:24px;background:#eee;color:#333;position:relative}
#plusMenu{position:absolute;bottom:58px;left:0;background:white;border:1px solid #ddd;border-radius:15px;padding:8px;box-shadow:0 8px 25px #0002;min-width:190px;z-index:10}
.tool{display:block;width:100%;padding:12px;text-align:left;border:0;background:white;border-radius:10px;font-size:15px}.tool:hover{background:#f2f2f2}
.image-message{max-width:800px;margin:12px auto;background:white;padding:10px;border-radius:18px;box-shadow:0 2px 10px #0001}
.generated-image{width:100%;max-height:700px;object-fit:contain;border-radius:12px;display:block}
.image-actions{display:flex;gap:8px;margin-top:8px}.image-actions a,.image-actions button{border:0;border-radius:10px;padding:9px 12px;text-decoration:none;background:#eee;color:#222;font-size:14px}
#chats{display:flex;gap:8px;padding:8px 12px;background:#fff;border-bottom:1px solid #ddd;overflow-x:auto}
#chats button{white-space:nowrap;border:1px solid #ddd;background:#f5f5f7;border-radius:10px;padding:7px 10px}#newchat{background:#007aff!important;color:#fff;border:0!important}
</style></head><body>
<div id="auth"><div class="card"><div class="logo">✦ STELLA 🌸</div><div class="sub" id="sub">Create your STELLA account</div><input id="username" placeholder="Username" autocomplete="username"><input id="password" type="password" placeholder="Password" autocomplete="current-password"><button onclick="auth()" id="authBtn">Create account</button><div class="error" id="error"></div><div class="switch" onclick="toggle()" id="switch">Already have an account? Log in</div></div></div>
<div id="app" class="hidden"><header><div class="brand">✦ STELLA</div><div class="user"><span id="welcome"></span><button id="logout" onclick="logout()">Log out</button></div></header><div id="chats"><button id="newchat" onclick="newChat()">+ New chat</button></div><div id="chat"></div><div id="inputArea"><div style="position:relative"><button id="plus" onclick="toggleTools()">+</button><div id="plusMenu" class="hidden"><button class="tool" onclick="startImageGeneration()">🎨 Generate an image</button></div></div><input id="message" placeholder="Message STELLA..." autocomplete="off"><button id="send" onclick="sendMessage()">Send</button></div></div>
<script>
let loginMode=false;
let conversationId=localStorage.getItem('stella_conversation_id');
const $=id=>document.getElementById(id);
function cacheKey(id){return 'stella_messages_'+id}
function saveMessages(){
    if(!conversationId)return;
    const messages=[...$('chat').querySelectorAll('.message')].map(m=>({text:m.textContent,type:m.classList.contains('user')?'user':'stella'}));
    localStorage.setItem(cacheKey(conversationId),JSON.stringify(messages));
}
function loadCachedMessages(id){
    if(!id)return false;
    try{const messages=JSON.parse(localStorage.getItem(cacheKey(id))||'[]');if(!messages.length)return false;$('chat').innerHTML='';messages.forEach(m=>add(m.text,m.type,false));scroll();return true}catch(e){return false}
}
function toggle(){loginMode=!loginMode;$('sub').textContent=loginMode?'Log in to STELLA':'Create your STELLA account';$('authBtn').textContent=loginMode?'Log in':'Create account';$('switch').textContent=loginMode?'Need an account? Create one':'Already have an account? Log in';$('error').textContent=''}
async function auth(){let u=$('username').value.trim(),p=$('password').value;if(!u||!p){$('error').textContent='Please enter a username and password.';return}try{let r=await fetch(loginMode?'/login':'/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(!r.ok||!d.success){$('error').textContent=d.error||'Something went wrong.';return}show(d.username||u)}catch(e){$('error').textContent='Could not connect to STELLA.'}}
async function check(){try{let r=await fetch('/me');let d=await r.json();if(d.logged_in)show(d.username)}catch(e){}}
async function show(u){$('auth').classList.add('hidden');$('app').classList.remove('hidden');$('welcome').textContent='Hi, '+u+'!';await loadConversations()}
async function logout(){await fetch('/logout',{method:'POST'});localStorage.removeItem('stella_conversation_id');location.reload()}
async function loadConversations(){let r=await fetch('/conversations');if(!r.ok){loadCachedMessages(conversationId);return}let d=await r.json();let box=$('chats');box.innerHTML='<button id="newchat" onclick="newChat()">+ New chat</button>';d.conversations.forEach(c=>{let b=document.createElement('button');b.textContent=c.title||'New chat';b.onclick=()=>loadConversation(c.id);box.appendChild(b)});if(d.conversations.length){const stored=conversationId&&d.conversations.some(c=>String(c.id)===String(conversationId));const target=stored?conversationId:d.conversations[0].id;await loadConversation(target)}else{loadCachedMessages(conversationId)}}
async function loadConversation(id){let r=await fetch('/conversation?id='+encodeURIComponent(id));if(!r.ok){loadCachedMessages(id);return}let d=await r.json();conversationId=String(id);localStorage.setItem('stella_conversation_id',conversationId);$('chat').innerHTML='';d.messages.forEach(m=>add(m.parts[0].text,m.role==='user'?'user':'stella',false));saveMessages();scroll()}
function renderWelcome(){$('chat').innerHTML='<div class="message stella">Hey! I\'m STELLA 🌸<br>Nice to meet you! What are we doing today?</div>'}
function newChat(){conversationId=null;localStorage.removeItem('stella_conversation_id');renderWelcome();$('message').focus()}
function toggleTools(){$('plusMenu').classList.toggle('hidden')}
function startImageGeneration(){
    $('plusMenu').classList.add('hidden');
    const prompt=window.prompt('What image should STELLA generate?');
    if(!prompt||!prompt.trim())return;
    generateImage(prompt.trim());
}
async function generateImage(prompt){
    add('Generate an image: '+prompt,'user');
    const status=add('Creating your image... 🎨','stella');
    try{
        const r=await fetch('/generate-image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt,conversation_id:conversationId})});
        const d=await r.json();
        if(r.status===401){location.reload();return}
        if(!r.ok){status.textContent=d.error||'Image generation is not configured yet.';saveMessages();return}
        status.remove();
        showGeneratedImage(d.image_url,prompt);
    }catch(e){status.textContent='Could not generate the image right now.';saveMessages()}
}
function showGeneratedImage(url,prompt){
    const wrap=document.createElement('div');wrap.className='image-message';
    const img=document.createElement('img');img.className='generated-image';img.src=url;img.alt=prompt;
    const actions=document.createElement('div');actions.className='image-actions';
    const download=document.createElement('a');download.href=url;download.download='stella-image.png';download.textContent='Download';download.target='_blank';
    const ask=document.createElement('button');ask.textContent='Continue chatting';ask.onclick=()=>{$('message').focus()};
    actions.appendChild(download);actions.appendChild(ask);wrap.appendChild(img);wrap.appendChild(actions);$('chat').appendChild(wrap);scroll();
}
async function sendMessage(){
    let text=$('message').value.trim();if(!text)return;add(text,'user');$('message').value='';let t=add('Thinking... ✨','stella');
    try{let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,conversation_id:conversationId})});let d=await r.json();if(r.status===401){location.reload();return}if(!r.ok){t.textContent=d.reply||'Something went wrong.';saveMessages();return}conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);t.textContent=d.reply;saveMessages();await loadConversations()}catch(e){t.textContent='Oops! Something went wrong. 😅';saveMessages()}scroll()
}
function add(text,type,save=true){let m=document.createElement('div');m.className='message '+type;m.textContent=text;$('chat').appendChild(m);scroll();if(save)saveMessages();return m}
function scroll(){$('chat').scrollTop=$('chat').scrollHeight}
$('message').addEventListener('keydown',e=>{if(e.key==='Enter')sendMessage()});$('password').addEventListener('keydown',e=>{if(e.key==='Enter')auth()});check();
</script></body></html>'''

def body(h):
    n=int(h.headers.get('Content-Length',0))
    return json.loads(h.rfile.read(n).decode('utf-8'))

def send(h,data,status=200,cookie=None):
    out=json.dumps(data).encode('utf-8')
    h.send_response(status)
    h.send_header('Content-Type','application/json')
    h.send_header('Content-Length',str(len(out)))
    if cookie:h.send_header('Set-Cookie',cookie)
    h.end_headers()
    h.wfile.write(out)

def token(h):
    for item in h.headers.get('Cookie','').split(';'):
        item=item.strip()
        if item.startswith('stella_session='):return item.split('=',1)[1]
    return None

def current_user(h):
    return get_user_from_session(token(h))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/':
            out=HTML.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out);return
        if self.path=='/me':
            uid=current_user(self);send(self,{'logged_in':bool(uid),'username':get_username(uid) if uid else None});return
        if self.path=='/conversations':
            uid=current_user(self)
            if not uid:send(self,{'conversations':[]},401);return
            send(self,{'conversations':get_conversations(uid)});return
        if self.path.startswith('/conversation?id='):
            uid=current_user(self)
            try:cid=int(self.path.split('=',1)[1])
            except:send(self,{'error':'Invalid conversation.'},400);return
            if not uid or not user_owns_conversation(uid,cid):send(self,{'error':'Not found.'},404);return
            send(self,{'messages':get_messages(cid)});return
        self.send_response(404);self.end_headers()

    def do_POST(self):
        if self.path=='/register':
            try:
                d=body(self);u=d.get('username','').strip();p=d.get('password','')
                if len(u)<3:raise ValueError('Username must be at least 3 characters.')
                if len(p)<6:raise ValueError('Password must be at least 6 characters.')
                uid=create_user(u,hash_password(p))
                if uid is None:raise ValueError('Username already exists.')
                t=create_session(uid);send(self,{'success':True,'username':u},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
            except Exception as e:send(self,{'success':False,'error':str(e)},400)
            return
        if self.path=='/login':
            try:
                d=body(self);u=d.get('username','').strip();p=d.get('password','');uid=verify_user(u,p)
                if uid is None:raise ValueError('Invalid username or password.')
                t=create_session(uid);send(self,{'success':True,'username':u},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
            except Exception as e:send(self,{'success':False,'error':str(e)},401)
            return
        if self.path=='/logout':
            delete_session(token(self));send(self,{'success':True},cookie='stella_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax');return
        if self.path=='/generate-image':
            uid=current_user(self)
            if not uid:send(self,{'error':'Please log in to generate images.'},401);return
            try:
                d=body(self);prompt=d.get('prompt','').strip()
                if not prompt:raise ValueError('Image prompt cannot be empty.')
                if not IMAGE_API_URL:
                    send(self,{'error':'Image generation UI is ready, but no image model is configured yet. We will connect the image model next.'},503);return
                payload={'prompt':prompt}
                headers={'Content-Type':'application/json'}
                if IMAGE_API_KEY:headers['Authorization']='Bearer '+IMAGE_API_KEY
                req=urllib.request.Request(IMAGE_API_URL,data=json.dumps(payload).encode('utf-8'),headers=headers,method='POST')
                with urllib.request.urlopen(req,timeout=120) as r:result=json.loads(r.read().decode('utf-8'))
                image_url=result.get('image_url') or result.get('url') or result.get('data')
                if not image_url:raise ValueError('Image provider did not return an image URL.')
                send(self,{'image_url':image_url})
            except Exception as e:send(self,{'error':'Image generation failed: '+str(e)},500)
            return
        if self.path!='/chat':self.send_response(404);self.end_headers();return
        uid=current_user(self)
        if not uid:send(self,{'reply':'Please log in to talk with STELLA.'},401);return
        try:
            d=body(self);message=d.get('message','').strip();cid=d.get('conversation_id')
            if not message:raise ValueError('Message cannot be empty.')
            if cid is None:cid=create_conversation(uid,message[:60])
            else:
                cid=int(cid)
                if not user_owns_conversation(uid,cid):raise ValueError('Invalid conversation.')
            history=get_messages(cid);add_message(cid,'user',message)
            contents=history+[{"role":"user","parts":[{"text":message}]}]
            payload={'systemInstruction':{'parts':[{'text':PERSONALITY}]},'contents':contents}
            req=urllib.request.Request(MODEL_URL,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json','x-goog-api-key':API_KEY},method='POST')
            with urllib.request.urlopen(req) as r:result=json.loads(r.read().decode('utf-8'))
            reply=''
            for part in result['candidates'][0]['content']['parts']:
                if not part.get('thought',False):reply=part.get('text','');break
            add_message(cid,'model',reply)
            send(self,{'reply':reply,'conversation_id':cid})
        except Exception as e:send(self,{'reply':'Something went wrong: '+str(e)},500)

create_database()
port=int(os.environ.get('PORT',10000))
server=HTTPServer(('0.0.0.0',port),Handler)
print('STELLA running on port',port)
server.serve_forever()
