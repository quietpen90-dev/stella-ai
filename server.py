import json, re
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from database import *
from config import API_KEY, VOICE_API_KEY, VOICE_MODEL, PERSONALITY, PLUGINS
from ai_service import generate_chat_reply, generate_image
from voice_service import create_voice_token
from frontend import HTML


def read_json(h):
    n=int(h.headers.get('Content-Length',0)); return json.loads(h.rfile.read(n).decode() or '{}')

def send_json(h,data,status=200,cookie=None):
    out=json.dumps(data).encode(); h.send_response(status); h.send_header('Content-Type','application/json'); h.send_header('Content-Length',str(len(out)))
    if cookie: h.send_header('Set-Cookie',cookie)
    h.end_headers(); h.wfile.write(out)

def token(h):
    for x in h.headers.get('Cookie','').split(';'):
        if x.strip().startswith('stella_session='): return x.strip().split('=',1)[1]
    return None

def uid(h): return get_user_from_session(token(h))

def cid_for(user_id,value,title='New chat'):
    if value in (None,'','null'): return create_conversation(user_id,title)
    cid=int(value)
    if not user_owns_conversation(user_id,cid): raise ValueError('Invalid conversation.')
    return cid

def make_title(text,attachments):
    clean=re.sub(r'\s+',' ',(text or '').strip())
    if clean: return clean[:60]
    if attachments: return ('Image: ' if attachments[0].get('type')=='image' else 'Video: ' if attachments[0].get('type')=='video' else 'File: ')+attachments[0].get('name','Attachment')[:45]
    return 'New chat'

def history_for(user_id,stored,settings):
    source=get_user_memory_messages(user_id,40) if settings['memory_enabled'] else stored
    history=[]
    for m in source:
        role=m.get('role')
        if role in ('user','model'):
            history.append({'role':role,'parts':[{'text':m.get('content',m.get('parts',[{'text':''}])[0].get('text',''))}]})
        elif role=='image':
            try:d=json.loads(m.get('content',''))
            except:d={}
            history.append({'role':'model','parts':[{'text':'STELLA previously generated an image with prompt: '+str(d.get('prompt',''))}]})
        elif role=='attachment':
            a=m.get('attachment',{}); history.append({'role':'user','parts':[{'text':'User attached '+a.get('type','file')+': '+a.get('name','Attachment')}]})
    return history

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p=urlparse(self.path); u=uid(self)
        if p.path=='/':
            out=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(out))); self.end_headers(); self.wfile.write(out); return
        if p.path=='/me': return send_json(self,{'logged_in':bool(u),'username':get_username(u) if u else None})
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
        if p.path in ('/register','/login'):
            try:
                d=read_json(self); name=d.get('username','').strip(); pw=d.get('password','')
                if p.path=='/register':
                    if len(name)<3 or len(pw)<6: raise ValueError('Username must be at least 3 characters and password at least 6 characters.')
                    x=create_user(name,hash_password(pw))
                    if x is None: raise ValueError('Username already exists.')
                else:
                    x=verify_user(name,pw)
                    if x is None: raise ValueError('Invalid username or password.')
                t=create_session(x); return send_json(self,{'success':True,'username':get_username(x)},cookie='stella_session='+t+'; HttpOnly; Path=/; SameSite=Lax')
            except Exception as e:return send_json(self,{'success':False,'error':str(e)},401 if p.path=='/login' else 400)
        if p.path=='/logout':delete_session(token(self));return send_json(self,{'success':True},cookie='stella_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax')
        if not u:return send_json(self,{'error':'Please log in first.'},401)
        try:
            if p.path=='/settings':
                d=read_json(self);return send_json(self,update_user_settings(u,d.get('theme'),d.get('memory_enabled')))
            if p.path=='/chat':
                d=read_json(self);msg=d.get('message','').strip();attachments=d.get('attachments') or [];cid=cid_for(u,d.get('conversation_id'),make_title(msg,attachments))
                stored=get_messages(cid); add_message(cid,'user',msg,attachments[0] if attachments else None)
                settings=get_user_settings(u); reply=generate_chat_reply(history_for(u,stored,settings),msg or ('The user attached '+attachments[0].get('type','file')+' named '+attachments[0].get('name','Attachment')+'.'))
                add_message(cid,'model',reply)
                if len(get_messages(cid))<=2:set_conversation_title(cid,make_title(msg,attachments))
                return send_json(self,{'reply':reply,'conversation_id':cid})
            if p.path=='/attachment':
                d=read_json(self);a={'type':d.get('type','file'),'name':d.get('name','Attachment'),'data':d.get('data','')};cid=cid_for(u,d.get('conversation_id'),make_title('',[a]));add_message(cid,'user','',a);return send_json(self,{'success':True,'conversation_id':cid})
            if p.path=='/generate-image':
                d=read_json(self);prompt=d.get('prompt','').strip();cid=cid_for(u,d.get('conversation_id'),prompt[:60] or 'Image');add_message(cid,'user',prompt);url=generate_image(prompt);add_message(cid,'image',json.dumps({'url':url,'prompt':prompt}));set_conversation_title(cid,prompt[:100] or 'Generated image');return send_json(self,{'image_url':url,'conversation_id':cid})
            if p.path=='/voice/token':
                d=read_json(self);cid=cid_for(u,d.get('conversation_id'),'Voice call with STELLA');ctx='\n'.join((('User: ' if x['role']=='user' else 'STELLA: ')+x['parts'][0]['text']) for x in get_messages(cid) if x['role'] in ('user','model'));result=create_voice_token(ctx);call=create_voice_call(u,cid,'gemini-live',result.get('name'));return send_json(self,{'success':True,'call_id':call,'conversation_id':cid,'token':result.get('name'),'model':VOICE_MODEL,'expires_at':result.get('expireTime')})
            if p.path=='/voice/end':
                d=read_json(self);call=get_voice_call(int(d['call_id']),u)
                if not call:raise ValueError('Voice call not found.')
                end_voice_call(call['id'],u);duration=int(d.get('duration',0));add_message(call['conversation_id'],'voice_call',f'{duration//60:02d}:{duration%60:02d}');return send_json(self,{'success':True})
            self.send_response(404);self.end_headers();return
        except Exception as e:return send_json(self,{'error':str(e),'reply':'Something went wrong: '+str(e)},500)

create_database()
port=int(__import__('os').environ.get('PORT',10000));server=HTTPServer(('0.0.0.0',port),Handler);print('STELLA running on port',port);server.serve_forever()
