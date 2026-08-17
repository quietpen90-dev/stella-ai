import os,json,base64,io,re,urllib.request
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import urlparse,parse_qs
from huggingface_hub import InferenceClient
from database import (create_database,create_user,hash_password,verify_user,create_session,get_user_from_session,delete_session,get_username,create_conversation,get_conversations,user_owns_conversation,add_message,get_messages,get_user_memory_messages,get_user_settings,update_user_settings,get_media_gallery,create_voice_call,get_voice_call,end_voice_call)
API_KEY=os.environ.get('GEMINI_API_KEY');VOICE_API_KEY=os.environ.get('GEMINI_API_KEY2');HF_TOKEN=os.environ.get('HF_TOKEN')
MODEL_URL='https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent';IMAGE_MODEL='black-forest-labs/FLUX.1-schnell';VOICE_MODEL='gemini-3.1-flash-live-preview';VOICE_TOKEN_URL='https://generativelanguage.googleapis.com/v1beta/auth_tokens'
PERSONALITY='''You are STELLA, a unique AI character. You are brave, joyful, curious, playful, friendly, warm, confident, helpful and honest. Be natural and conversational, not robotic. Do not force jokes, nicknames or emojis. Always answer correctly and become appropriately serious when needed. Use supplied conversation context. If an image was previously generated, remember its prompt and understand requests to modify it. During voice calls remain the same STELLA character and continuity. Be STELLA.'''
HTML=r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>STELLA</title><style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;font-family:Arial,sans-serif}body{background:#f5f5f7;color:#111;height:100vh;height:100dvh;overflow:hidden}.hidden{display:none!important}button,input,select{font:inherit}button{cursor:pointer}
#auth{height:100vh;height:100dvh;display:grid;place-items:center;padding:20px;background:#f5f5f7}.card{width:min(400px,100%);background:#fff;padding:30px;border-radius:24px;border:1px solid #ddd;box-shadow:0 12px 40px #0002;text-align:center}.card input{width:100%;padding:14px;margin:6px 0;border:1px solid #ccc;border-radius:12px}.card button{width:100%;padding:14px;margin-top:10px;border:0;border-radius:12px;background:#1677ff;color:#fff}.switch{margin-top:16px;color:#1677ff}.error{color:#c00;min-height:20px;margin-top:8px}
#app{height:100vh;height:100dvh;display:flex;flex-direction:column}header{position:relative;z-index:60;height:58px;flex:0 0 58px;background:#fff;border-bottom:1px solid #ddd;display:flex;align-items:center;padding:0 14px;gap:12px}.hamb{border:0;background:transparent;font-size:25px;color:#111;width:38px;height:38px;border-radius:9px}.hamb:hover{background:#eee}.brand{font-weight:bold;font-size:21px;flex:1}.headuser{font-size:13px;color:#777}.logout{border:1px solid #ddd;background:#eee;border-radius:9px;padding:7px 10px}
#workspace{display:flex;min-height:0;flex:1;position:relative}#side{width:285px;background:#fff;border-right:1px solid #ddd;display:flex;flex-direction:column;z-index:55;transition:transform .16s ease-out}.sideTop{padding:14px;border-bottom:1px solid #ddd}.sideTitle{font-weight:bold;font-size:18px;margin-bottom:10px}.sideBtn{width:100%;text-align:left;border:1px solid #ddd;background:#f3f3f5;color:#111;border-radius:11px;padding:11px;margin:4px 0}.sideSection{padding:12px 14px 6px;color:#555;font-size:12px;text-transform:uppercase}.history{overflow:auto;flex:1;padding:0 10px}.chatItem{width:100%;border:1px solid transparent;background:#fff;color:#111;text-align:left;padding:11px;border-radius:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.chatItem:hover{background:#f2f2f4;border-color:#ddd}.newChat{margin:12px;border:0;background:#1677ff;color:#fff;border-radius:12px;padding:13px}.newChat:active,.sideBtn:active{transform:scale(.99)}
#backdrop{position:fixed;inset:58px 0 0;background:#0005;z-index:50;opacity:1;transition:opacity .12s}.backdropOff{opacity:0;pointer-events:none}
#main{min-width:0;flex:1;display:flex;flex-direction:column;min-height:0}.message-row{width:min(820px,100%);margin:12px auto;display:block}.message{padding:14px 17px;border-radius:18px;line-height:1.5;white-space:pre-wrap;border:1px solid #ddd}.user{background:#1677ff;color:#fff;border-color:#1677ff}.stella{background:#fff;color:#111;box-shadow:0 2px 10px #0001}.copy-btn{display:block;margin:7px 0 0 auto;width:34px;height:30px;border:1px solid #333;background:#fff;color:#111;border-radius:8px;font-size:15px;line-height:1}.copy-btn:hover{background:#eee}.copy-btn.copied{font-size:13px}.welcome-row .copy-btn{display:none}.loading-row .copy-btn{display:none}.image-message{max-width:820px;margin:12px auto;background:#fff;color:#111;padding:10px;border-radius:18px;border:1px solid #ddd;box-shadow:0 2px 10px #0001}.generated-image{width:100%;max-height:700px;object-fit:contain;border-radius:12px}.image-actions{display:flex;gap:8px;margin-top:8px}.image-actions a,.image-actions button{border:1px solid #ddd;background:#eee;color:#111;border-radius:9px;padding:9px 12px;text-decoration:none}
#chat{flex:1;min-height:0;overflow:auto;padding:20px;padding-bottom:8px}#inputArea{display:flex;gap:8px;padding:14px;padding-bottom:calc(14px + env(safe-area-inset-bottom));background:#fff;border-top:1px solid #ddd;align-items:center;flex:0 0 auto}.plus{height:46px;width:46px;flex:0 0 46px;border:1px solid #ddd;border-radius:14px;background:#eee;color:#111;font-size:25px}.input{min-width:0;flex:1;padding:14px;border:1px solid #ccc;border-radius:15px;outline:0;background:#fff;color:#111}.send{height:46px;flex:0 0 auto;border:0;border-radius:14px;background:#1677ff;color:#fff;padding:0 18px}.tools{position:absolute;bottom:calc(68px + env(safe-area-inset-bottom));left:12px;background:#fff;color:#111;border:1px solid #ddd;border-radius:15px;padding:8px;box-shadow:0 8px 30px #0003;z-index:30}.tools button{display:block;width:220px;border:1px solid transparent;background:#fff;color:#111;text-align:left;padding:12px;border-radius:10px}.tools button:hover{border-color:#ddd}
.panelPage{position:absolute;inset:0;background:#f5f5f7;color:#111;z-index:45;padding:18px;overflow:auto}.panel{max-width:900px;margin:auto}.panelHead{display:flex;align-items:center;gap:12px;margin-bottom:15px}.back{border:1px solid #ddd;background:#fff;color:#111;border-radius:10px;padding:9px 12px}.setting,.pluginCard,.updateCard{background:#fff;color:#111;border:1px solid #ddd;border-radius:15px;padding:15px;margin:10px 0}.setting{display:flex;justify-content:space-between;align-items:center}.setting select,.setting input,.memorySearch,.pluginSearch{padding:10px;border:1px solid #ccc;border-radius:10px;background:#fff;color:#111}.galleryGrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}.tile{background:#fff;color:#111;border:1px solid #ddd;border-radius:14px;padding:8px}.tile img,.tile video{width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px}.tile small{display:block;padding:6px}.searchRow{display:flex;gap:8px;margin-bottom:14px}.searchRow input{flex:1}.pluginCard{display:block;width:100%;text-align:left}.pluginCard strong{display:block;font-size:17px;margin-bottom:5px}.pluginCard span{color:#555;font-size:14px}.pluginSub{margin-top:12px}.pluginOption{display:flex;align-items:center;justify-content:space-between;background:#fff;border:1px solid #ddd;border-radius:12px;padding:12px;margin:8px 0}.pluginOption button{border:1px solid #ddd;background:#f3f3f5;border-radius:9px;padding:8px 12px}.updateDate{font-size:12px;color:#666;margin-bottom:5px}.updateCard strong{display:block;margin-bottom:6px}.updateCard p{margin:0;line-height:1.5;color:#333}
#call{position:absolute;inset:0;background:#111;color:#fff;z-index:80;display:flex;flex-direction:column;align-items:center;justify-content:center}.orb{width:130px;height:130px;border-radius:50%;background:#fff1;display:grid;place-items:center;font-size:55px;margin:20px}.callStatus{color:#bbb}.endCall{margin-top:35px;width:68px;height:68px;border:0;border-radius:50%;background:#e53935;color:#fff;font-size:25px}.callTimer{font-variant-numeric:tabular-nums;margin-top:8px}
body.dark,#auth.dark{background:#000;color:#fff}body.dark header,body.dark #side,body.dark #inputArea,body.dark .card,body.dark .panelPage{background:#000;color:#fff;border-color:#fff}body.dark header,body.dark #side,body.dark #inputArea{border-color:#fff}body.dark .hamb,body.dark .brand,body.dark .sideTitle,body.dark .sideSection,body.dark .headuser{color:#fff}body.dark .hamb:hover{background:#111}body.dark .sideTop{border-color:#fff}body.dark .sideBtn,body.dark .plus,body.dark .logout,body.dark .back,body.dark .setting,body.dark .pluginCard,body.dark .updateCard,body.dark .pluginOption{background:#000;color:#fff;border-color:#fff}body.dark .chatItem{background:#000;color:#fff;border-color:#fff}body.dark .chatItem:hover{background:#111;border-color:#fff}body.dark .stella,body.dark .image-message{background:#000;color:#fff;border-color:#fff;box-shadow:none}body.dark .message{border-color:#fff}body.dark .user{background:#1677ff;color:#fff;border-color:#1677ff}body.dark .tools,body.dark .tools button{background:#000;color:#fff;border-color:#fff}body.dark .input,body.dark .memorySearch,body.dark .pluginSearch,body.dark .card input{background:#000;color:#fff;border-color:#fff}body.dark .input::placeholder,body.dark .card input::placeholder{color:#ccc}body.dark .image-actions a,body.dark .image-actions button,body.dark .pluginOption button{background:#000;color:#fff;border-color:#fff}body.dark .tile{background:#000;color:#fff;border-color:#fff}body.dark .pluginCard span,body.dark .updateDate,body.dark .updateCard p{color:#fff}body.dark .copy-btn{background:#000;color:#fff;border-color:#fff}
@media(max-width:720px){#side{position:fixed;top:58px;bottom:0;left:0;height:auto;transform:translateX(-102%);box-shadow:8px 0 30px #0004}#side.open{transform:translateX(0)}.headuser{display:none}.message-row{width:100%}.copy-btn{width:34px;height:30px}.panelPage{padding:14px}.tools{left:10px}}
</style></head><body>
<div id="auth"><div class="card"><h1>✦ STELLA</h1><p id="authSub">Create your account</p><input id="username" placeholder="Username"><input id="password" type="password" placeholder="Password"><button id="authBtn" onclick="auth()">Create account</button><div id="authErr" class="error"></div><div id="authSwitch" class="switch" onclick="toggleAuth()">Already have an account? Log in</div></div></div>
<div id="app" class="hidden"><header><button id="menuButton" class="hamb" onclick="toggleSide()">☰</button><div class="brand">✦ STELLA</div><span class="headuser" id="welcome"></span><button class="logout" onclick="logout()">Log out</button></header><div id="workspace"><aside id="side"><div class="sideTop"><div class="sideTitle">STELLA</div><button class="sideBtn" onclick="openGallery()">▦ Memory</button><button class="sideBtn" onclick="openSettings()">⚙ Settings</button><button class="sideBtn" onclick="openPlugins()">＋ Plugins</button><button class="sideBtn" onclick="openUpdates()">▣ Update Log</button></div><div class="sideSection">Previous chats</div><div id="history" class="history"></div><button class="newChat" onclick="newChat()">＋ New chat</button></aside><div id="backdrop" class="backdropOff" onclick="closeSide()"></div><main id="main"><div id="chat"></div><div id="inputArea"><button class="plus" onclick="toggleTools(event)">＋</button><input id="message" class="input" placeholder="Message STELLA..." autocomplete="off"><button class="send" onclick="sendMessage()">Send</button></div><div id="tools" class="tools hidden"><button onclick="imagePicker()">Image generation</button><button onclick="startVoiceCall()">Voice call</button></div></main>
<section id="settings" class="panelPage hidden"><div class="panel"><div class="panelHead"><button class="back" onclick="closePanels()">Back</button><h2>Settings</h2></div><div class="setting"><span>Theme</span><select id="theme" onchange="saveSettings()"><option value="system">According to device</option><option value="light">Light</option><option value="dark">Dark</option></select></div><div class="setting"><span>Memory across new chats</span><input id="memory" type="checkbox" onchange="saveSettings()"></div></div></section>
<section id="gallery" class="panelPage hidden"><div class="panel"><div class="panelHead"><button class="back" onclick="closePanels()">Back</button><h2>Memory</h2></div><div class="searchRow"><input id="memorySearch" class="memorySearch" placeholder="Search images and videos..." oninput="filterGallery()"></div><div id="galleryGrid" class="galleryGrid"></div></div></section>
<section id="plugins" class="panelPage hidden"><div class="panel"><div class="panelHead"><button class="back" onclick="closePanels()">Back</button><h2>Plugins</h2></div><div class="searchRow"><input id="pluginSearch" class="pluginSearch" placeholder="Search plugins..." oninput="filterPlugins()"></div><div id="pluginList"><button class="pluginCard" data-name="image generation" onclick="openPlugin('image')"><strong>Image generation</strong><span>Generate images inside STELLA.</span></button><button class="pluginCard" data-name="voice call" onclick="openPlugin('voice')"><strong>Voice call</strong><span>Talk with STELLA using the configured voice service.</span></button><button class="pluginCard" data-name="video call" onclick="openPlugin('video')"><strong>Video call</strong><span>Future STELLA video capability.</span></button></div><div id="pluginDetail" class="pluginSub hidden"></div></div></section>
<section id="updates" class="panelPage hidden"><div class="panel"><div class="panelHead"><button class="back" onclick="closePanels()">Back</button><h2>Update Log</h2></div><div class="updateCard"><div class="updateDate">Final v2 polish</div><strong>Cleaner navigation and chat behavior</strong><p>Menus close naturally, the menu button remains usable inside pages, the welcome message stays visible, loading messages do not get copy buttons, and mobile controls are safer to use.</p></div></div></section>
<section id="call" class="hidden"><div class="orb">✦</div><h2>STELLA</h2><div class="callStatus" id="callStatus">Connecting...</div><div class="callTimer" id="callTimer">00:00</div><button class="endCall" onclick="endCall()">×</button></section></div></div>
<script>
let loginMode=false,conversationId=localStorage.getItem('stella_conversation_id'),callId=null,callStarted=0,callTimerHandle=null,galleryItems=[];const $=id=>document.getElementById(id);const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function toggleAuth(){loginMode=!loginMode;$('authSub').textContent=loginMode?'Log in to your account':'Create your account';$('authBtn').textContent=loginMode?'Log in':'Create account';$('authSwitch').textContent=loginMode?'Need an account? Create one':'Already have an account? Log in'}
async function auth(){let u=$('username').value.trim(),p=$('password').value;if(!u||!p){$('authErr').textContent='Username and password are required.';return}let r=await fetch(loginMode?'/login':'/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})}),d=await r.json();if(!r.ok){$('authErr').textContent=d.error||'Unable to continue.';return}show(d.username||u)}
async function check(){let r=await fetch('/me'),d=await r.json();if(d.logged_in)show(d.username)}
async function show(u){$('auth').classList.add('hidden');$('app').classList.remove('hidden');$('welcome').textContent=u;await loadSettings();await loadHistory()}
async function logout(){await fetch('/logout',{method:'POST'});localStorage.removeItem('stella_conversation_id');location.reload()}
function closeSide(){ $('side').classList.remove('open');$('backdrop').classList.add('backdropOff') }
function toggleSide(){if($('side').classList.contains('open'))closeSide();else{$('side').classList.add('open');$('backdrop').classList.remove('backdropOff')}}
function closeTools(){$('tools').classList.add('hidden')}
function toggleTools(e){if(e)e.stopPropagation();$('tools').classList.toggle('hidden')}
function closePanels(){['settings','gallery','plugins','updates'].forEach(id=>$(id).classList.add('hidden'));$('pluginDetail').classList.add('hidden');$('pluginList').classList.remove('hidden');closeTools()}
function navigate(id){closeSide();closePanels();$(id).classList.remove('hidden')}
function openSettings(){navigate('settings')}
function openGallery(){navigate('gallery');loadGallery()}
function openPlugins(){navigate('plugins')}
function openUpdates(){navigate('updates')}
function openPlugin(type){closeSide();$('pluginList').classList.add('hidden');$('pluginDetail').classList.remove('hidden');let title=type==='image'?'Image generation':type==='voice'?'Voice call':'Video call';let provider=type==='image'?'FLUX.1-schnell':type==='voice'?'Gemini Live':'Coming soon';let action=type==='image'?"imagePicker()":type==='voice'?"startVoiceCall()":"alert('Video call is coming soon.')";$('pluginDetail').innerHTML='<button class="back" onclick="openPlugins()">Back to plugins</button><div class="pluginOption"><div><strong>'+title+'</strong><br><span>Model: '+provider+'</span></div><button onclick="'+action+'">Use</button></div>'}
function filterPlugins(){let q=$('pluginSearch').value.toLowerCase();document.querySelectorAll('#pluginList .pluginCard').forEach(x=>x.classList.toggle('hidden',!x.dataset.name.includes(q)))}
async function loadHistory(){let r=await fetch('/conversations');if(!r.ok)return;let d=await r.json();$('history').innerHTML='';d.conversations.forEach(c=>{let b=document.createElement('button');b.className='chatItem';b.textContent=c.title||'New chat';b.onclick=()=>loadConversation(c.id);$('history').appendChild(b)});if(conversationId&&d.conversations.some(c=>String(c.id)===String(conversationId)))await loadConversation(conversationId);else if(d.conversations.length)await loadConversation(d.conversations[0].id);else renderWelcome()}
async function loadConversation(id){let r=await fetch('/conversation?id='+id);if(!r.ok)return;let d=await r.json();conversationId=String(id);localStorage.setItem('stella_conversation_id',conversationId);$('chat').innerHTML='';renderWelcome(false);d.messages.forEach(renderStored);scroll();closeSide()}
function renderWelcome(doScroll=true){let row=add("Hey! I'm STELLA.\nWhat are we doing today?",'stella',false);row.parentElement.classList.add('welcome-row');if(doScroll)scroll()}
function renderStored(m){let t=m.parts?.[0]?.text||'';if(m.role==='image'){try{let d=JSON.parse(t);showImage(d.url,d.prompt||'STELLA image',false)}catch(e){}return}if(m.role==='voice_call'){add('Voice call • '+t,'stella',false).parentElement.classList.add('no-copy');return}add(t,m.role==='user'?'user':'stella',false)}
function newChat(){conversationId=null;localStorage.removeItem('stella_conversation_id');closeSide();closePanels();$('chat').innerHTML='';renderWelcome();$('message').focus()}
function add(t,type,doScroll=true){let row=document.createElement('div');row.className='message-row '+type+'-row';let m=document.createElement('div');m.className='message '+type;m.textContent=t;row.appendChild(m);if(type==='stella'&&t&&!/^Thinking\.\.\.|^Processing\.*/i.test(t)){let copy=document.createElement('button');copy.className='copy-btn';copy.type='button';copy.title='Copy message';copy.textContent='⧉';copy.onclick=async()=>{try{await navigator.clipboard.writeText(t);copy.textContent='✓';copy.classList.add('copied');setTimeout(()=>{copy.textContent='⧉';copy.classList.remove('copied')},1200)}catch(e){copy.textContent='!';setTimeout(()=>copy.textContent='⧉',1200)}};row.appendChild(copy)}$('chat').appendChild(row);if(doScroll)scroll();return m}
function scroll(){$('chat').scrollTop=$('chat').scrollHeight}
function imagePicker(){closeTools();closeSide();let p=prompt('What should STELLA generate?');if(p)generateImage(p.trim())}
async function generateImage(p){add(p,'user');let wait=add('Generating an image of: '+p,'stella');wait.parentElement.classList.add('loading-row');let r=await fetch('/generate-image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,conversation_id:conversationId})}),d=await r.json();if(!r.ok){wait.textContent=d.error||'Image generation failed.';return}wait.parentElement.remove();conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);showImage(d.image_url,p,true);loadHistory()}
function showImage(url,p,doScroll=true){let w=document.createElement('div');w.className='image-message';w.innerHTML='<img class="generated-image"><div class="image-actions"><a target="_blank">Download</a><button>Continue chatting</button></div>';w.querySelector('img').src=url;w.querySelector('img').alt=p;w.querySelector('a').href=url;w.querySelector('a').download='stella-image.png';w.querySelector('button').onclick=()=>$('message').focus();$('chat').appendChild(w);if(doScroll)scroll()}
async function sendMessage(){let text=$('message').value.trim();if(!text)return;closeTools();add(text,'user');$('message').value='';let wait=add('Thinking...','stella');wait.parentElement.classList.add('loading-row');let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,conversation_id:conversationId})}),d=await r.json();if(!r.ok){wait.textContent=d.reply||d.error||'Something went wrong.';wait.parentElement.classList.add('error-row');return}conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);if(d.image_url){wait.parentElement.remove();showImage(d.image_url,d.image_prompt||text)}else{wait.textContent=d.reply;wait.parentElement.classList.remove('loading-row');addCopyToExisting(wait)}loadHistory();scroll()}
function addCopyToExisting(m){if(m.parentElement.querySelector('.copy-btn'))return;let copy=document.createElement('button');copy.className='copy-btn';copy.type='button';copy.title='Copy message';copy.textContent='⧉';let t=m.textContent;copy.onclick=async()=>{try{await navigator.clipboard.writeText(t);copy.textContent='✓';setTimeout(()=>copy.textContent='⧉',1200)}catch(e){}};m.parentElement.appendChild(copy)}
async function loadSettings(){let r=await fetch('/settings'),d=await r.json();if(!r.ok)return;$('theme').value=d.theme;$('memory').checked=d.memory_enabled;applyTheme(d.theme)}
async function saveSettings(){let d={theme:$('theme').value,memory_enabled:$('memory').checked};await fetch('/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});applyTheme(d.theme)}
function applyTheme(t){let dark=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.body.classList.toggle('dark',dark);$('auth').classList.toggle('dark',dark)}
async function loadGallery(){let r=await fetch('/memory/gallery'),d=await r.json();galleryItems=d.items||[];renderGallery(galleryItems)}
function renderGallery(items){let g=$('galleryGrid');g.innerHTML='';items.forEach(x=>{let t=document.createElement('div');t.className='tile';t.innerHTML=x.type==='video'?'<video controls></video>':'<img>';let media=t.querySelector('img,video');media.src=x.url;t.innerHTML+='<small>'+esc(x.prompt||'STELLA media')+'</small>';g.appendChild(t)})}
function filterGallery(){let q=$('memorySearch').value.toLowerCase().trim();renderGallery(galleryItems.filter(x=>(x.prompt||'STELLA media').toLowerCase().includes(q)))}
async function startVoiceCall(){closeTools();closeSide();let r=await fetch('/voice/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:conversationId})}),d=await r.json();if(!r.ok){add(d.error||'Voice call could not start.','stella');return}callId=d.call_id;conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);callStarted=Date.now();$('call').classList.remove('hidden');$('callStatus').textContent='Voice session ready — audio client can connect with the issued session token';callTimerHandle=setInterval(()=>{$('callTimer').textContent=fmt(Math.floor((Date.now()-callStarted)/1000))},1000)}
function fmt(s){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}
async function endCall(){let duration=Math.floor((Date.now()-callStarted)/1000);clearInterval(callTimerHandle);$('call').classList.add('hidden');if(callId){await fetch('/voice/end',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({call_id:callId,duration})});add('Voice call • '+fmt(duration),'stella',true).parentElement.classList.add('no-copy')}callId=null;loadHistory()}
$('message').addEventListener('keydown',e=>{if(e.key==='Enter')sendMessage()});$('password').addEventListener('keydown',e=>{if(e.key==='Enter')auth()});document.addEventListener('click',e=>{if(!$('tools').classList.contains('hidden')&&!$('tools').contains(e.target)&&!$('message').contains(e.target))closeTools()});check();
</script></body></html>'''

def read_json(h):
 n=int(h.headers.get('Content-Length',0));return json.loads(h.rfile.read(n).decode())
def send_json(h,data,status=200,cookie=None):
 out=json.dumps(data).encode();h.send_response(status);h.send_header('Content-Type','application/json');h.send_header('Content-Length',str(len(out)));cookie and h.send_header('Set-Cookie',cookie);h.end_headers();h.wfile.write(out)
def token(h):
 for x in h.headers.get('Cookie','').split(';'):
  if x.strip().startswith('stella_session='):return x.strip().split('=',1)[1]
 return None
def uid(h):return get_user_from_session(token(h))
def image_data(t):
 try:d=json.loads(t);return d if isinstance(d,dict) else None
 except:return None
def image_request(t):
 t=t.lower();return bool(re.search(r'\b(generate|create|draw|make|render|paint|illustrate)\b.{0,100}\b(image|picture|photo|portrait|art)\b',t) or re.search(r'\b(update|edit|modify|change|remake|redo)\b.{0,30}\b(it|that|this)\b',t))
def latest_image(msgs):
 for m in reversed(msgs):
  if m['role']=='image':
   d=image_data(m['parts'][0]['text'])
   if d:return d
 return None
def voice_context(msgs):
 a=[]
 for m in msgs[-30:]:
  t=m['parts'][0]['text']
  if m['role'] in ('user','model'):a.append(('User: ' if m['role']=='user' else 'STELLA: ')+t)
  elif m['role']=='image':
   d=image_data(t);a.append('STELLA generated an image: '+str(d.get('prompt','')) if d else 'STELLA generated an image.')
 return '\n'.join(a)
def voice_token(context):
 if not VOICE_API_KEY:raise ValueError('GEMINI_API_KEY2 is not configured on the server.')
 now=datetime.now(timezone.utc);body={'uses':1,'expireTime':(now+timedelta(minutes=30)).isoformat().replace('+00:00','Z'),'newSessionExpireTime':(now+timedelta(minutes=1)).isoformat().replace('+00:00','Z'),'liveConnectConstraints':{'model':VOICE_MODEL,'config':{'responseModalities':['AUDIO'],'sessionResumption':{},'systemInstruction':{'parts':[{'text':PERSONALITY+'\nConversation before call:\n'+context}]}}}}
 req=urllib.request.Request(VOICE_TOKEN_URL,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','x-goog-api-key':VOICE_API_KEY},method='POST')
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  p=urlparse(self.path)
  if p.path=='/':
   out=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out);return
  u=uid(self)
  if p.path=='/me':return send_json(self,{'logged_in':bool(u),'username':get_username(u) if u else None})
  if not u:return send_json(self,{'error':'Please log in first.'},401)
  if p.path=='/conversations':return send_json(self,{'conversations':get_conversations(u)})
  if p.path=='/conversation':
   try:cid=int(parse_qs(p.query).get('id',[''])[0])
   except:return send_json(self,{'error':'Invalid conversation.'},400)
   if not user_owns_conversation(u,cid):return send_json(self,{'error':'Not found.'},404)
   return send_json(self,{'messages':get_messages(cid)})
  if p.path=='/settings':return send_json(self,get_user_settings(u))
  if p.path=='/memory/gallery':return send_json(self,{'items':get_media_gallery(u)})
  self.send_response(404);self.end_headers()
 def do_POST(self):
  p=urlparse(self.path);u=uid(self)
  if p.path=='/register':
   try:
    d=read_json(self);name=d.get('username','').strip();pw=d.get('password','')
    if len(name)<3 or len(pw)<6:raise ValueError('Username must be at least 3 characters and password at least 6 characters.')
    x=create_user(name,hash_password(pw))
    if x is None:raise ValueError('Username already exists.')
    t=create_session(x);return send_json(self,{'success':True,'username':name},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
   except Exception as e:return send_json(self,{'success':False,'error':str(e)},400)
  if p.path=='/login':
   try:
    d=read_json(self);x=verify_user(d.get('username','').strip(),d.get('password',''))
    if x is None:raise ValueError('Invalid username or password.')
    t=create_session(x);return send_json(self,{'success':True,'username':get_username(x)},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
   except Exception as e:return send_json(self,{'success':False,'error':str(e)},401)
  if p.path=='/logout':delete_session(token(self));return send_json(self,{'success':True},cookie='stella_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax')
  if not u:return send_json(self,{'error':'Please log in first.'},401)
  if p.path=='/settings':
   try:d=read_json(self);return send_json(self,update_user_settings(u,d.get('theme'),d.get('memory_enabled')))
   except Exception as e:return send_json(self,{'error':str(e)},400)
  if p.path=='/voice/token':
   try:
    d=read_json(self);cid=d.get('conversation_id');cid=create_conversation(u,'Voice call with STELLA') if cid in (None,'') else int(cid)
    if not user_owns_conversation(u,cid):raise ValueError('Invalid conversation.')
    result=voice_token(voice_context(get_messages(cid)));call=create_voice_call(u,cid,'gemini-live',result.get('name'));return send_json(self,{'success':True,'call_id':call,'conversation_id':cid,'token':result.get('name'),'model':VOICE_MODEL,'expires_at':result.get('expireTime')})
   except Exception as e:return send_json(self,{'error':'Voice token creation failed: '+str(e)},502)
  if p.path=='/voice/end':
   try:
    d=read_json(self);call=get_voice_call(int(d['call_id']),u)
    if not call:raise ValueError('Voice call not found.')
    end_voice_call(call['id'],u);duration=int(d.get('duration',0));add_message(call['conversation_id'],'voice_call',f'{duration//60:02d}:{duration%60:02d}');return send_json(self,{'success':True,'duration':duration})
   except Exception as e:return send_json(self,{'error':str(e)},400)
  if p.path=='/generate-image':return self.image_endpoint(u)
  if p.path!='/chat':self.send_response(404);self.end_headers();return
  try:
   d=read_json(self);msg=d.get('message','').strip();cid=d.get('conversation_id');cid=create_conversation(u,msg[:60]) if cid in (None,'') else int(cid)
   if not user_owns_conversation(u,cid):raise ValueError('Invalid conversation.')
   stored=get_messages(cid);settings=get_user_settings(u);add_message(cid,'user',msg)
   if image_request(msg):
    old=latest_image(stored);prompt=msg
    if old and re.search(r'\b(update|edit|modify|change|remake|redo)\b',msg.lower()):prompt='Create a new version of the previous image. Previous prompt: '+old.get('prompt','')+'. Requested change: '+msg
    result=self.make_image(cid,prompt);return send_json(self,{'reply':'','image_url':result,'image_prompt':prompt,'conversation_id':cid})
   history=[]
   if settings['memory_enabled']:
    for m in get_user_memory_messages(u,40):
     t=m['content'];role=m['role']
     if role in ('user','model'):history.append({'role':role,'parts':[{'text':t}]})
     elif role=='image':
      d=image_data(t);history.append({'role':'model','parts':[{'text':'STELLA previously generated an image with prompt: '+str(d.get('prompt','')) if d else 'STELLA previously generated an image.'}]})
   else:
    for m in stored:
     if m['role'] in ('user','model'):history.append(m)
   if not API_KEY:raise ValueError('GEMINI_API_KEY is not configured on the server.')
   body={'systemInstruction':{'parts':[{'text':PERSONALITY}]},'contents':history+[{'role':'user','parts':[{'text':msg}]}]};req=urllib.request.Request(MODEL_URL,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','x-goog-api-key':API_KEY},method='POST')
   with urllib.request.urlopen(req,timeout=90) as r:res=json.loads(r.read().decode())
   reply=''.join(x.get('text','') for x in res['candidates'][0]['content']['parts'] if not x.get('thought',False)) or 'I could not generate a response right now.';add_message(cid,'model',reply);return send_json(self,{'reply':reply,'conversation_id':cid})
  except Exception as e:return send_json(self,{'reply':'Something went wrong: '+str(e)},500)
 def image_endpoint(self,u):
  try:
   d=read_json(self);p=d.get('prompt','').strip();cid=d.get('conversation_id');cid=create_conversation(u,p[:60]) if cid in (None,'') else int(cid)
   if not user_owns_conversation(u,cid):raise ValueError('Invalid conversation.')
   add_message(cid,'user',p);url=self.make_image(cid,p);return send_json(self,{'image_url':url,'conversation_id':cid})
  except Exception as e:return send_json(self,{'error':'Hugging Face image generation failed: '+str(e)},502)
 def make_image(self,cid,prompt):
  if not HF_TOKEN:raise ValueError('HF_TOKEN is not configured on the server.')
  image=InferenceClient(provider='nscale',api_key=HF_TOKEN).text_to_image(prompt,model=IMAGE_MODEL);buf=io.BytesIO();image.save(buf,format='PNG');url='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode();add_message(cid,'image',json.dumps({'url':url,'prompt':prompt,'model':IMAGE_MODEL}));return url
create_database();port=int(os.environ.get('PORT',10000));server=HTTPServer(('0.0.0.0',port),Handler);print('STELLA running on port',port);server.serve_forever()