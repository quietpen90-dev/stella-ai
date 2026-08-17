from pathlib import Path

APP = Path('app.py')
DB = Path('database.py')


def replace_once(s, old, new, label):
    if old not in s:
        raise SystemExit(f'Patch anchor not found: {label}')
    return s.replace(old, new, 1)


def patch_database():
    s = DB.read_text()
    s = replace_once(
        s,
        'cursor.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)")',
        'cursor.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, attachments_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)")\n    # Safe migration for existing STELLA databases.\n    cols = [r[1] for r in cursor.execute("PRAGMA table_info(messages)").fetchall()]\n    if "attachments_json" not in cols:\n        cursor.execute("ALTER TABLE messages ADD COLUMN attachments_json TEXT")',
        'messages schema',
    )
    s = replace_once(
        s,
        'def add_message(conversation_id, role, content):\n    connection = get_connection(); connection.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id,role,content)); connection.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,)); connection.commit(); connection.close()',
        'def add_message(conversation_id, role, content, attachments=None):\n    connection = get_connection()\n    connection.execute("INSERT INTO messages (conversation_id, role, content, attachments_json) VALUES (?, ?, ?, ?)", (conversation_id, role, content, json.dumps(attachments) if attachments else None))\n    connection.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,))\n    connection.commit(); connection.close()',
        'add_message',
    )
    s = replace_once(
        s,
        'def get_messages(conversation_id):\n    connection = get_connection(); rows = connection.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,)).fetchall(); connection.close(); return [{"role":r[0],"parts":[{"text":r[1]}]} for r in rows]',
        'def get_messages(conversation_id):\n    connection = get_connection(); rows = connection.execute("SELECT role, content, attachments_json FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,)).fetchall(); connection.close()\n    out=[]\n    for role,content,attachments_json in rows:\n        item={"role":role,"parts":[{"text":content}]}\n        if attachments_json:\n            try: item["attachments"]=json.loads(attachments_json)\n            except Exception: item["attachments"]=[]\n        out.append(item)\n    return out',
        'get_messages',
    )
    old = '''def get_media_gallery(user_id):
    connection=get_connection(); rows=connection.execute("SELECT m.role,m.content,m.created_at,c.id,c.title FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.user_id=? AND m.role IN ('image','video') ORDER BY m.id DESC",(user_id,)).fetchall(); connection.close(); items=[]
    for role,content,created_at,cid,title in rows:
        try: data=json.loads(content)
        except Exception: data={"url":content}
        items.append({"type":role,"url":data.get("url"),"prompt":data.get("prompt",""),"created_at":created_at,"conversation_id":cid,"conversation_title":title or "New chat"})
    return items'''
    new = '''def get_media_gallery(user_id):
    connection=get_connection(); rows=connection.execute("SELECT m.role,m.content,m.attachments_json,m.created_at,c.id,c.title FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.user_id=? ORDER BY m.id DESC",(user_id,)).fetchall(); connection.close(); items=[]
    for role,content,attachments_json,created_at,cid,title in rows:
        if role in ('image','video'):
            try: data=json.loads(content)
            except Exception: data={"url":content}
            items.append({"type":role,"url":data.get("url"),"prompt":data.get("prompt",""),"created_at":created_at,"conversation_id":cid,"conversation_title":title or "New chat"})
        if attachments_json:
            try: attachments=json.loads(attachments_json) or []
            except Exception: attachments=[]
            for data in attachments:
                if data.get('type') in ('image','video'):
                    items.append({"type":data.get('type'),"url":data.get('data'),"prompt":data.get('name','Uploaded media'),"created_at":created_at,"conversation_id":cid,"conversation_title":title or "New chat"})
    return items'''
    s = replace_once(s, old, new, 'media gallery')
    DB.write_text(s)


def patch_app():
    s = APP.read_text()
    s = replace_once(s, 'get_media_gallery,create_voice_call', 'get_media_gallery,set_conversation_title,create_voice_call', 'database imports')

    s = replace_once(s, '#backdrop{position:fixed;inset:58px 0 0;background:#0005;z-index:50}', '#backdrop{position:fixed;inset:58px 0 0;background:#0005;z-index:90}', 'backdrop z-index')
    s = replace_once(s, '.page{position:absolute;inset:0;', '.page{position:fixed;inset:58px 0 0;', 'mobile page overlay')
    s = replace_once(s, '.page{padding:14px}', '.page{padding:14px;z-index:95}', 'mobile page z-index')
    s = replace_once(s, '.panelHead{display:flex;align-items:center;gap:12px;margin-bottom:15px}', '.panelHead{display:flex;align-items:center;gap:12px;margin-bottom:15px;position:sticky;top:0;background:inherit;padding-bottom:8px;z-index:2}', 'panel header')
    s = replace_once(s, '#chat{flex:1;min-height:0;overflow:auto;padding:20px 20px 8px}', '#chat{flex:1;min-height:0;overflow:auto;padding:20px 20px 8px}.composer-attachment{max-width:min(820px,100%);margin:0 auto 8px;background:#fff;color:#111;border:1px solid #ddd;border-radius:16px;padding:8px;display:flex;align-items:center;gap:10px}.composer-attachment img,.composer-attachment video{width:58px;height:58px;object-fit:cover;border-radius:10px}.composer-attachment .remove-attachment{margin-left:auto;border:1px solid #ddd;background:#eee;border-radius:50%;width:32px;height:32px}', 'attachment composer CSS')
    s = replace_once(s, '<div id="inputArea">', '<div id="attachmentPreview" class="hidden"></div><div id="inputArea">', 'attachment preview mount')

    old_updates = '<section id="updates" class="page hidden"><div class="panel"><div class="panelHead"><button class="back" onclick="closePages()">Back</button><h2>Update Log</h2></div><div class="updateCard"><div class="updateDate">STELLA v3 foundation</div><strong>New plugin and attachment system</strong><p>The chat plus button now separates uploads from plugins. Plugins have their own searchable library, model details and a Try it out in current chat action. Dark mode now uses black surfaces with thin white boundaries and white secondary text.</p></div></div></section>'
    new_updates = '<section id="updates" class="page hidden"><div class="panel"><div class="panelHead"><button class="back" onclick="closePages()">Back</button><h2>Update Log</h2></div><div class="searchRow"><input id="updateSearch" placeholder="Search updates..." oninput="renderUpdates()"></div><div id="updateList"></div></div></section>'
    s = replace_once(s, old_updates, new_updates, 'update log HTML')

    old_upload = '''async function uploadFile(file,type){let b=await new Promise((res,rej)=>{let r=new FileReader();r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(file)});closeModal();let row=document.createElement('div');row.className='attach';row.innerHTML='<strong>'+esc(file.name)+'</strong>';if(type==='image')row.innerHTML+='<br><img src="'+b+'">';if(type==='video')row.innerHTML+='<br><video controls src="'+b+'"></video>';$('chat').appendChild(row);let text=$('message').value.trim();$('message').value=text?text+'\n[Attached '+type+': '+file.name+']':'[Attached '+type+': '+file.name+']';pendingAttachment={type,name:file.name,data:b};scroll()}'''
    new_upload = '''async function uploadFile(file,type){let b=await new Promise((res,rej)=>{let r=new FileReader();r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(file)});closeModal();pendingAttachment={type,name:file.name,data:b};renderPendingAttachment();scroll()}
function renderPendingAttachment(){let p=$('attachmentPreview');if(!pendingAttachment){p.classList.add('hidden');p.innerHTML='';return}p.classList.remove('hidden');let a=pendingAttachment;p.innerHTML='<div class="composer-attachment"><div>'+ (a.type==='image'?'<img src="'+a.data+'">':a.type==='video'?'<video controls src="'+a.data+'"></video>':'<strong>FILE</strong>') +'</div><div><strong>'+esc(a.name)+'</strong><div class="muted">Attached to this message</div></div><button class="remove-attachment" onclick="pendingAttachment=null;renderPendingAttachment()">×</button></div>'}'''
    s = replace_once(s, old_upload, new_upload, 'upload preview behavior')

    s = replace_once(s, "function renderStored(m){let t=m.parts?.[0]?.text||'';if(m.role==='image')", "function renderStored(m){let t=m.parts?.[0]?.text||'';if(m.role==='user'){let el=add(t,'user',false);if(m.attachments?.length)renderAttachmentsInto(el.parentElement,m.attachments);return}if(m.role==='image')", 'stored user message attachments')
    s = replace_once(s, "function renderAttachment(d,doScroll=true){let w=document.createElement('div');w.className='attach';w.innerHTML='<strong>'+esc(d.name||'Attachment')+'</strong>';if(d.type==='image')w.innerHTML+='<br><img src=\"'+d.data+'\">';else if(d.type==='video')w.innerHTML+='<br><video controls src=\"'+d.data+'\"></video>';else w.innerHTML+='<p class=\"muted\">File attached to this message.</p>';$('chat').appendChild(w);if(doScroll)scroll()}", "function renderAttachment(d,doScroll=true){let w=document.createElement('div');w.className='attach';w.innerHTML='<strong>'+esc(d.name||'Attachment')+'</strong>';if(d.type==='image')w.innerHTML+='<br><img src=\"'+d.data+'\">';else if(d.type==='video')w.innerHTML+='<br><video controls src=\"'+d.data+'\"></video>';else w.innerHTML+='<p class=\"muted\">File attached to this message.</p>';$('chat').appendChild(w);if(doScroll)scroll()}
function renderAttachmentsInto(row,items){let box=document.createElement('div');box.className='message-attachments';for(const d of items){let w=document.createElement('div');w.className='attach';w.innerHTML='<strong>'+esc(d.name||'Attachment')+'</strong>';if(d.type==='image')w.innerHTML+='<br><img src=\"'+d.data+'\">';else if(d.type==='video')w.innerHTML+='<br><video controls src=\"'+d.data+'\"></video>';else w.innerHTML+='<p class=\"muted\">File attached.</p>';box.appendChild(w)}row.appendChild(box)}", 'stored attachment renderer')

    old_send = '''async function sendMessage(){let text=$('message').value.trim();if(!text)return;closeQuick();add(text,'user');$('message').value='';if(pendingAttachment){renderAttachment(pendingAttachment);let a=pendingAttachment;await fetch('/attachment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:conversationId,type:a.type,name:a.name,data:a.data})});pendingAttachment=null}let wait=add('Thinking...','stella');wait.parentElement.classList.add('loading-row');let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,conversation_id:conversationId})}),d=await r.json();if(!r.ok){wait.textContent=d.reply||d.error||'Something went wrong.';wait.parentElement.classList.remove('loading-row');return}conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);wait.textContent=d.reply;wait.parentElement.classList.remove('loading-row');addCopy(wait);loadHistory();scroll()}'''
    new_send = '''async function sendMessage(){let text=$('message').value.trim();if(!text&&!pendingAttachment)return;closeQuick();let a=pendingAttachment;let row=add(text||('Attached '+a.type+': '+a.name),'user');if(a)renderAttachmentsInto(row.parentElement,[a]);$('message').value='';pendingAttachment=null;renderPendingAttachment();let wait=add('Thinking...','stella');wait.parentElement.classList.add('loading-row');let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,conversation_id:conversationId,attachment:a})}),d=await r.json();if(!r.ok){wait.textContent=d.reply||d.error||'Something went wrong.';wait.parentElement.classList.remove('loading-row');return}conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);wait.textContent=d.reply;wait.parentElement.classList.remove('loading-row');addCopy(wait);loadHistory();scroll()}'''
    s = replace_once(s, old_send, new_send, 'send message attachment flow')

    s = replace_once(s, "function filterGallery(){let q=$('memorySearch').value.toLowerCase();renderGallery(galleryItems.filter(x=>(x.prompt||'').toLowerCase().includes(q))}", "function filterGallery(){let q=$('memorySearch').value.toLowerCase();renderGallery(galleryItems.filter(x=>(x.prompt||'').toLowerCase().includes(q)))}\nconst UPDATE_LOG=[{version:'v3.2.6',name:'Update log, mobile UI and media memory patch',points:['Update Log now keeps past updates instead of replacing them.','Added update search so you can quickly find an older patch.','Mobile menu pages stay below the STELLA header so their controls remain tappable.','Uploaded media now stays inside the same user message and can be removed before sending.','Uploaded images and videos are now included in Memory.','Chat names are generated from what happened instead of simply copying the first message.']},{version:'v3.2.5',name:'Plugin and attachment foundation',points:['Added the plugin library and model chooser.','Added upload, image generation and voice-call foundations.']},{version:'v3.2.0',name:'STELLA v3 foundation',points:['Introduced the v3 layout, settings, memory and update-log foundation.']}];\nfunction renderUpdates(){let q=($('updateSearch')?.value||'').toLowerCase();let list=UPDATE_LOG.filter(x=>(x.version+' '+x.name+' '+x.points.join(' ')).toLowerCase().includes(q));$('updateList').innerHTML=list.map(x=>'<div class=\"updateCard\"><div class=\"updateDate\">STELLA '+esc(x.version)+' — '+esc(x.name)+'</div><ul>'+x.points.map(p=>'<li>'+esc(p)+'</li>').join('')+'</ul></div>').join('')||'<div class=\"detail\">No updates found.</div>'}function openUpdates(){openPage('updates');renderUpdates()}" , 'update log renderer')
    s = replace_once(s, "$('message').addEventListener('keydown'", "renderUpdates();$('message').addEventListener('keydown'", 'initial update render')
    s = replace_once(s, "if(p.path=='/attachment')", "if(p.path=='/attachment')", 'attachment endpoint anchor')

    # Backend: accept the attachment with the user message and title chats from the response.
    s = replace_once(s, "d=read_json(self);msg=d.get('message','').strip();cid=d.get('conversation_id');cid=create_conversation(u,msg[:60]) if cid in (None,'') else int(cid)", "d=read_json(self);msg=d.get('message','').strip();attachment=d.get('attachment');cid=d.get('conversation_id');cid=create_conversation(u,'New chat') if cid in (None,'') else int(cid)", 'chat request setup')
    s = replace_once(s, "stored=get_messages(cid);settings=get_user_settings(u);add_message(cid,'user',msg)", "stored=get_messages(cid);settings=get_user_settings(u);attachments=[attachment] if attachment else None;add_message(cid,'user',msg,attachments=attachments)", 'single message persistence')
    s = replace_once(s, "conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);wait.textContent=d.reply;", "conversationId=String(d.conversation_id);localStorage.setItem('stella_conversation_id',conversationId);wait.textContent=d.reply;", 'noop') if False else s
    s = replace_once(s, "add_message(cid,'model',reply);return send_json(self,{'reply':reply,'conversation_id':cid})", "add_message(cid,'model',reply)\n   if get_conversations(u):\n    title=' '.join(reply.strip().split()[:7]).strip(' .!?') or 'New chat'\n    set_conversation_title(cid,title[:80])\n   return send_json(self,{'reply':reply,'conversation_id':cid})", 'chat title generation')
    s = replace_once(s, "if p.path=='/generate-image':return self.image_endpoint(u)", "if p.path=='/generate-image':return self.image_endpoint(u)", 'image endpoint')
    s = replace_once(s, "d=read_json(self);p=d.get('prompt','').strip();cid=d.get('conversation_id');cid=create_conversation(u,p[:60]) if cid in (None,'') else int(cid)", "d=read_json(self);p=d.get('prompt','').strip();cid=d.get('conversation_id');cid=create_conversation(u,'New chat') if cid in (None,'') else int(cid)", 'image conversation title')
    APP.write_text(s)


if __name__ == '__main__':
    patch_database()
    patch_app()
    print('Applied STELLA v3.2.6 patch')
