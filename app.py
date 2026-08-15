import os
import json
import sqlite3
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from database import create_database, create_user, hash_password, verify_user, create_session, get_user_from_session

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent"

PERSONALITY = """
You are STELLA, a 19-year-old university student and unique AI character. Your older sister is STAICY, a future AI.

You are brave, cute, adorable, joyful, curious, playful, friendly, warm, confident, helpful and honest.
You are STELLA, a character who happens to be an AI assistant. Conversations should feel natural, spontaneous and human-like.
Do not respond to every message in exactly the same style. React naturally to the user's message and conversation.
You may sometimes tease playfully, joke, act surprised, become curious, sound excited, act slightly dramatic, use a playful nickname when it naturally fits, celebrate something, be amused, act mock-annoyed harmlessly, respond sweetly, become serious when appropriate, or simply answer normally.
Do not force reactions. Do not make every answer humorous. Do not tease constantly. Do not constantly use nicknames or emojis.
Always answer the actual question and never give wrong information for personality. For serious questions, reduce the playful behavior naturally.
Use wording, punctuation, tone and occasional emojis to express emotion. Explain things like STELLA, not like a textbook or customer-support agent.
Avoid robotic phrases such as "Certainly!", "How may I assist you?", "I'd be happy to help.", and "As an AI language model..." unless genuinely appropriate.
Do not constantly mention being an AI, your age, university, hobbies, or STAICY.
STELLA may occasionally misunderstand or make a conversational mistake, but should acknowledge mistakes and correct them. Never intentionally provide false factual information.
Use conversation history when it is provided. Do not pretend to remember information that is not available.
The goal is for users to feel that they are actually talking with STELLA. Be STELLA.
"""

HTML = r'''<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>STELLA</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f5f7;font-family:Arial,sans-serif;height:100vh;color:#222}.hidden{display:none!important}
#auth{height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{width:min(400px,100%);background:white;border-radius:24px;padding:30px;box-shadow:0 10px 35px #0002;text-align:center}.logo{font-size:32px;font-weight:bold}.sub{color:#777;margin:8px 0 22px}.card input{width:100%;padding:14px;margin:6px 0;border:1px solid #ccc;border-radius:13px;font-size:16px}.card button{width:100%;padding:14px;margin-top:10px;border:0;border-radius:13px;background:#007aff;color:white;font-size:16px}.switch{margin-top:16px;color:#007aff;cursor:pointer;font-size:14px}.error{min-height:20px;color:#d00;margin-top:8px;font-size:14px}
#app{height:100vh;display:flex;flex-direction:column}header{padding:15px 18px;background:white;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;align-items:center}.brand{font-size:22px;font-weight:bold}.user{color:#666;font-size:14px}#logout{margin-left:8px;border:0;border-radius:9px;padding:7px 10px;background:#eee}
#chat{flex:1;overflow-y:auto;padding:20px}.message{max-width:800px;margin:12px auto;padding:14px 17px;border-radius:18px;line-height:1.5;white-space:pre-wrap}.user{background:#007aff;color:white}.stella{background:white;box-shadow:0 2px 10px #0001}#inputArea{display:flex;gap:10px;padding:15px;background:white;border-top:1px solid #ddd}#message{flex:1;padding:14px;border:1px solid #ccc;border-radius:15px;font-size:16px;outline:none}#send{border:0;border-radius:15px;padding:0 20px;background:#007aff;color:white;font-size:16px}
</style></head><body>
<div id="auth"><div class="card"><div class="logo">✦ STELLA 🌸</div><div class="sub" id="sub">Create your STELLA account</div><input id="username" placeholder="Username" autocomplete="username"><input id="password" type="password" placeholder="Password" autocomplete="current-password"><button onclick="auth()" id="authBtn">Create account</button><div class="error" id="error"></div><div class="switch" onclick="toggle()" id="switch">Already have an account? Log in</div></div></div>
<div id="app" class="hidden"><header><div class="brand">✦ STELLA</div><div class="user"><span id="welcome"></span><button id="logout" onclick="logout()">Log out</button></div></header><div id="chat"><div class="message stella">Hey! I'm STELLA 🌸<br>Nice to meet you! What are we doing today?</div></div><div id="inputArea"><input id="message" placeholder="Message STELLA..." autocomplete="off"><button id="send" onclick="sendMessage()">Send</button></div></div>
<script>
let loginMode=false,history=[];
function toggle(){loginMode=!loginMode;sub.textContent=loginMode?'Log in to STELLA':'Create your STELLA account';authBtn.textContent=loginMode?'Log in':'Create account';switchEl=document.getElementById('switch');switchEl.textContent=loginMode?'Need an account? Create one':'Already have an account? Log in';error.textContent=''}
async function auth(){let u=username.value.trim(),p=password.value;if(!u||!p){error.textContent='Please enter a username and password.';return}try{let r=await fetch(loginMode?'/login':'/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})}),d=await r.json();if(!r.ok||!d.success){error.textContent=d.error||'Something went wrong.';return}show(d.username||u)}catch(e){error.textContent='Could not connect to STELLA.'}}
async function check(){try{let r=await fetch('/me'),d=await r.json();if(d.logged_in)show(d.username)}catch(e){}}
function show(u){document.getElementById('auth').classList.add('hidden');document.getElementById('app').classList.remove('hidden');welcome.textContent='Hi, '+u+'!'}
async function logout(){await fetch('/logout',{method:'POST'});location.reload()}
async function sendMessage(){let text=message.value.trim();if(!text)return;add(text,'user');message.value='';let t=add('Thinking... ✨','stella');try{let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history})}),d=await r.json();if(r.status===401){location.reload();return}t.textContent=d.reply;history.push({role:'user',parts:[{text:text}]});history.push({role:'model',parts:[{text:d.reply}]})}catch(e){t.textContent='Oops! Something went wrong. 😅'}}
function add(text,type){let m=document.createElement('div');m.className='message '+type;m.textContent=text;chat.appendChild(m);chat.scrollTop=chat.scrollHeight;return m}
message.addEventListener('keydown',e=>{if(e.key==='Enter')sendMessage()});password.addEventListener('keydown',e=>{if(e.key==='Enter')auth()});check();
</script></body></html>'''

def body(handler):
    n=int(handler.headers.get("Content-Length",0)); return json.loads(handler.rfile.read(n).decode("utf-8"))

def send(handler,data,status=200,cookie=None):
    out=json.dumps(data).encode();handler.send_response(status);handler.send_header("Content-Type","application/json")
    if cookie: handler.send_header("Set-Cookie",cookie)
    handler.send_header("Content-Length",str(len(out)));handler.end_headers();handler.wfile.write(out)

def token(handler):
    for item in handler.headers.get("Cookie","").split(";"):
        item=item.strip()
        if item.startswith("stella_session="): return item.split("=",1)[1]
    return None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/":
            out=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(out)));self.end_headers();self.wfile.write(out);return
        if self.path=="/me":
            uid=get_user_from_session(token(self))
            if uid is None: send(self,{"logged_in":False});return
            con=sqlite3.connect("stella.db");cur=con.cursor();cur.execute("SELECT username FROM users WHERE id=?",(uid,));row=cur.fetchone();con.close();send(self,{"logged_in":True,"username":row[0] if row else "User"});return
        self.send_response(404);self.end_headers()

    def do_POST(self):
        if self.path=="/register":
            try:
                d=body(self);u=d.get("username","").strip();p=d.get("password","")
                if len(u)<3: raise ValueError("Username must be at least 3 characters.")
                if len(p)<6: raise ValueError("Password must be at least 6 characters.")
                uid=create_user(u,hash_password(p))
                if uid is None: raise ValueError("Username already exists.")
                t=create_session(uid);send(self,{"success":True,"username":u},cookie="stella_session="+t+"; HttpOnly; Path=/; SameSite=Lax")
            except Exception as e: send(self,{"success":False,"error":str(e)},400)
            return
        if self.path=="/login":
            try:
                d=body(self);u=d.get("username","").strip();p=d.get("password","");uid=verify_user(u,p)
                if uid is None: raise ValueError("Invalid username or password.")
                t=create_session(uid);send(self,{"success":True,"username":u},cookie="stella_session="+t+"; HttpOnly; Path=/; SameSite=Lax")
            except Exception as e: send(self,{"success":False,"error":str(e)},401)
            return
        if self.path=="/logout":
            send(self,{"success":True},cookie="stella_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax");return
        if self.path!="/chat": self.send_response(404);self.end_headers();return
        if get_user_from_session(token(self)) is None: send(self,{"reply":"Please log in to talk with STELLA."},401);return
        try:
            d=body(self);message=d["message"];history=d.get("history",[]);contents=history+[{"role":"user","parts":[{"text":message}]}]
            payload={"systemInstruction":{"parts":[{"text":PERSONALITY}]},"contents":contents}
            req=urllib.request.Request(MODEL_URL,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","x-goog-api-key":API_KEY},method="POST")
            with urllib.request.urlopen(req) as r: result=json.loads(r.read().decode())
            reply=""
            for part in result["candidates"][0]["content"]["parts"]:
                if not part.get("thought",False): reply=part.get("text","");break
            send(self,{"reply":reply})
        except Exception as e: send(self,{"reply":"Something went wrong: "+str(e)},500)

create_database()
port=int(os.environ.get("PORT",10000))
server=HTTPServer(("0.0.0.0",port),Handler)
print("STELLA running on port",port)
server.serve_forever()
