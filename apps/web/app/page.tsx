'use client';
import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';

const API=process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
type User={id:string;display_name:string};
type Conversation={id:string;display_name:string;last_message:string|null};
type Message={id:string;client_id:string;sender_id:string;body:string;sent_at:string;read_at:string|null};
async function request<T>(path:string, options:RequestInit={}):Promise<T> {
  let r: Response;
  try { r=await fetch(`${API}/api${path}`,{...options,credentials:'include',headers:{'Content-Type':'application/json',...options.headers}}); }
  catch { throw new Error('Cannot reach the messaging service. Check that the API is running and try again.'); }
  if(!r.ok) { const error=await r.json().catch(()=>({})); throw new Error(typeof error.message==='string'?error.message:'The request failed. Try again.'); }
  return r.json();
}
const post=<T,>(path:string,body:unknown)=>request<T>(path,{method:'POST',body:JSON.stringify(body)});

export default function Home() {
  const [user,setUser]=useState<User|null>(null),[checking,setChecking]=useState(true);
  const [purpose,setPurpose]=useState<'signin'|'register'>('signin'),[phone,setPhone]=useState(''),[name,setName]=useState(''),[code,setCode]=useState(''),[codeSent,setCodeSent]=useState(false);
  const [notice,setNotice]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [conversations,setConversations]=useState<Conversation[]>([]),[selected,setSelected]=useState<string|null>(null),[messages,setMessages]=useState<Message[]>([]),[draft,setDraft]=useState(''),[contact,setContact]=useState(''),[contactOpen,setContactOpen]=useState(false),[loadingMessages,setLoadingMessages]=useState(false),[hasOlder,setHasOlder]=useState(false),[theme,setTheme]=useState<'light'|'dark'>('light');
  const selectedRef=useRef(selected); selectedRef.current=selected;
  const pending=useRef<{id:string;body:string}|null>(null);
  const refreshConversations=useCallback(async()=>{setConversations(await request<Conversation[]>('/conversations'));},[]);
  const loadMessages=useCallback(async(id:string)=>{setLoadingMessages(true); try { const rows=await request<Message[]>(`/conversations/${id}/messages`); if(selectedRef.current===id){setMessages(rows);setHasOlder(rows.length===50);} await post(`/conversations/${id}/read`,{}); } finally {setLoadingMessages(false);} },[]);
  useEffect(()=>{request<User>('/auth/me').then(setUser).catch(()=>{}).finally(()=>setChecking(false)); const saved=localStorage.getItem('theme'); if(saved==='dark') setTheme('dark');},[]);
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('theme',theme);},[theme]);
  useEffect(()=>{if(!user)return; refreshConversations().catch(e=>setError(e.message)); const socket=io(API,{withCredentials:true});
    socket.on('connect',()=>{refreshConversations().catch(e=>setError(e.message));const id=selectedRef.current;if(id)loadMessages(id).catch(e=>setError(e.message));});
    socket.on('conversation:changed',({conversation_id}:{conversation_id:string})=>{refreshConversations().catch(e=>setError(e.message));if(selectedRef.current===conversation_id)loadMessages(conversation_id).catch(e=>setError(e.message));});
    return ()=>{socket.disconnect();}; },[user,refreshConversations,loadMessages]);
  async function act(fn:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await fn();}catch(e){setError(e instanceof Error?e.message:'Something went wrong.');}finally{setBusy(false);}}
  function changePurpose(p:'signin'|'register'){setPurpose(p);setCodeSent(false);setCode('');setError('');setNotice('');}
  async function requestCode(e:FormEvent){e.preventDefault();await act(async()=>{const r=await post<{message:string}>('/auth/request-code',{phone,purpose});setCodeSent(true);setNotice(r.message+' In local development, find the code in the API logs.');});}
  async function verify(e:FormEvent){e.preventDefault();await act(async()=>{const r=await post<{message:string}>('/auth/verify',{phone,purpose,code,...(purpose==='register'?{display_name:name}:{})});if(purpose==='register'){changePurpose('signin');setNotice(r.message);}else{setUser(await request<User>('/auth/me'));setNotice('');}});}
  async function choose(id:string){setSelected(id);selectedRef.current=id;setMessages([]);setError('');try{await loadMessages(id);}catch(e){setError(e instanceof Error?e.message:'Could not load messages.');}}
  async function send(e:FormEvent){e.preventDefault();const body=draft.trim();if(!selected||!body)return;const item=pending.current?.body===body?pending.current:{id:crypto.randomUUID(),body};pending.current=item;await act(async()=>{await post(`/conversations/${selected}/messages`,{client_id:item.id,body:item.body});pending.current=null;setDraft('');await loadMessages(selected);});}
  async function older(){if(!selected||!messages.length)return;await act(async()=>{const rows=await request<Message[]>(`/conversations/${selected}/messages?before=${messages[0].id}`);setMessages(current=>[...rows,...current.filter(x=>!rows.some(y=>y.id===x.id))]);setHasOlder(rows.length===50);});}
  if(checking)return <main className="center"><p role="status">Checking your session...</p></main>;
  return <main className={user?'workspace':'auth-page'}>
    {!user ? <section className="auth" aria-labelledby="auth-title">
      <div className="brand"><span className="brand-mark" aria-hidden="true">C</span><span>Commonplace</span></div>
      <p className="eyebrow">A place for conversations</p><h1 id="auth-title">{purpose==='signin'?'Welcome back.':'Create your account.'}</h1>
      <p className="intro">{purpose==='signin'?'Sign in with your phone number to continue.':'Verify your phone number, then sign in with a new code.'}</p>
      <div className="tabs" aria-label="Account action"><button type="button" className={purpose==='signin'?'active':''} onClick={()=>changePurpose('signin')}>Sign in</button><button type="button" className={purpose==='register'?'active':''} onClick={()=>changePurpose('register')}>Register</button></div>
      <form onSubmit={codeSent?verify:requestCode}>
        <label htmlFor="phone">Phone number</label><input id="phone" type="tel" autoComplete="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="Include country code, e.g. +84" required disabled={codeSent}/>
        {purpose==='register'&&<><label htmlFor="name">Display name</label><input id="name" value={name} onChange={e=>setName(e.target.value)} autoComplete="name" maxLength={80} required/></>}
        {codeSent&&<><label htmlFor="code">Verification code</label><input id="code" value={code} onChange={e=>setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required/></>}
        <button className="primary" disabled={busy}>{busy?'Please wait...':codeSent?'Verify code':'Send verification code'}</button>
        {codeSent&&<button type="button" className="text-button" onClick={()=>{setCodeSent(false);setCode('');}}>Change phone number</button>}
      </form>
      {notice&&<p className="notice" role="status">{notice}</p>}{error&&<p className="error" role="alert">{error}</p>}
      <p className="privacy">Local development build. The server can access messages; end-to-end encryption is not implemented.</p>
    </section> : <>
      <aside className={`sidebar ${selected?'mobile-hidden':''}`}>
        <div className="sidebar-head"><div className="brand"><span className="brand-mark" aria-hidden="true">C</span><span>Commonplace</span></div><button className="text-button" onClick={()=>setTheme(theme==='light'?'dark':'light')} aria-label={`Switch to ${theme==='light'?'dark':'light'} theme`}>{theme==='light'?'Dark':'Light'}</button></div>
        <div className="list-heading"><div><p className="eyebrow">YOUR SPACE</p><h1>Conversations</h1></div><button className="add" onClick={()=>setContactOpen(!contactOpen)} aria-expanded={contactOpen}>+ Add contact</button></div>
        {contactOpen&&<form className="contact-form" onSubmit={e=>{e.preventDefault();void act(async()=>{const r=await post<{message:string}>('/contacts',{phone:contact});setNotice(r.message);setContact('');await refreshConversations();});}}><label htmlFor="contact">Their phone number</label><input id="contact" type="tel" value={contact} onChange={e=>setContact(e.target.value)} placeholder="Include country code" required/><button className="primary" disabled={busy}>Save contact</button><p>Both people must add each other before a conversation appears.</p></form>}
        <nav className="conversation-list" aria-label="Conversations">{conversations.length?conversations.map(c=><button key={c.id} className={`conversation ${selected===c.id?'selected':''}`} onClick={()=>void choose(c.id)}><span className="avatar" aria-hidden="true">{c.display_name.slice(0,1).toUpperCase()}</span><span className="conversation-copy"><strong>{c.display_name}</strong><small>{c.last_message||'Start a conversation'}</small></span></button>):<p className="empty-list">No conversations yet. Add a contact to begin.</p>}</nav>
        <div className="account"><div><strong>{user.display_name}</strong><small>Signed in</small></div><button className="text-button" onClick={()=>void act(async()=>{await post('/auth/logout',{});setUser(null);setSelected(null);setMessages([]);setConversations([]);})}>Sign out</button></div>
      </aside>
      <section className={`chat ${!selected?'mobile-hidden':''}`} aria-label="Conversation">
        {selected ? <><header className="chat-head"><button className="back" onClick={()=>{setSelected(null);selectedRef.current=null;}}>Back</button><div><h2>{conversations.find(c=>c.id===selected)?.display_name||'Conversation'}</h2><p>Messages are stored on the server</p></div></header>
          <div className="message-scroll" aria-live="polite">{hasOlder&&<button className="load" disabled={busy} onClick={()=>void older()}>Load older messages</button>}{loadingMessages&&!messages.length?<p className="state">Loading messages...</p>:!messages.length?<div className="chat-empty"><h2>Start the conversation</h2><p>Messages you send will appear here.</p></div>:messages.map(m=><article key={m.id} className={`message ${m.sender_id===user.id?'mine':''}`}><p>{m.body}</p><small><time dateTime={m.sent_at}>{new Date(m.sent_at).toLocaleString([], {dateStyle:'medium',timeStyle:'short'})}</time>{m.sender_id===user.id&&(m.read_at?' · Read':' · Sent')}</small></article>)}</div>
          <form className="composer" onSubmit={send}><label htmlFor="message">Message</label><div><textarea id="message" rows={2} maxLength={5000} value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Write a message"/><button className="primary" disabled={busy||!draft.trim()}>Send</button></div><p>Text messages are retained until deleted. Deletion is not yet available in this build.</p></form></>:<div className="welcome"><span className="brand-mark large" aria-hidden="true">C</span><h2>Keep the conversation going.</h2><p>Choose a conversation, or add a contact to start one.</p></div>}
      </section>
      {(notice||error)&&<div className={`toast ${error?'error':''}`} role={error?'alert':'status'}>{error||notice}<button onClick={()=>{setError('');setNotice('');}} aria-label="Dismiss message">×</button></div>}
    </>}
  </main>;
}
