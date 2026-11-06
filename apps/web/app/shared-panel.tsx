'use client';
import { useCallback, useEffect, useRef, useState } from 'react';

const API=process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
type Category='media'|'files'|'links';
type Item={id:string;body:string;sent_at:string;filename:string|null;mime_type:string|null;size_bytes:number|null};
type Page={items:Item[];has_more:boolean};

function linksIn(text:string):string[] {
  return (text.match(/https?:\/\/[^\s<>]+/gi)||[]).map(url=>url.replace(/[.,!?;:]+$/,'')).filter(Boolean);
}

export default function SharedPanel({conversation,name,revision,onClose}:{conversation:string;name:string;revision:number;onClose:()=>void}) {
  const [category,setCategory]=useState<Category>('media');
  const [items,setItems]=useState<Item[]>([]);
  const [more,setMore]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [reload,setReload]=useState(0);
  const generation=useRef(0);
  const load=useCallback(async(before?:string,signal?:AbortSignal):Promise<Page>=>{
    const params=new URLSearchParams({type:category}); if(before)params.set('before',before);
    const response=await fetch(`${API}/api/conversations/${conversation}/shared?${params}`,{credentials:'include',signal});
    if(!response.ok)throw new Error('Could not load shared items.');
    return response.json();
  },[category,conversation]);
  useEffect(()=>{
    const controller=new AbortController(); generation.current++; setLoading(true);setError('');setItems([]);setMore(false);
    load(undefined,controller.signal).then(page=>{setItems(page.items);setMore(page.has_more);}).catch(e=>{if(e.name!=='AbortError')setError('Could not load shared items.');}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[load,revision,reload]);
  async function loadMore(){
    if(!items.length)return;const currentGeneration=generation.current;setLoading(true);setError('');
    try{const page=await load(items[items.length-1].id);if(currentGeneration===generation.current){setItems(current=>[...current,...page.items.filter(item=>!current.some(existing=>existing.id===item.id))]);setMore(page.has_more);}}
    catch{if(currentGeneration===generation.current)setError('Could not load more items.');}finally{if(currentGeneration===generation.current)setLoading(false);}
  }
  return <aside className="shared-panel" aria-label={`Shared items with ${name}`}>
    <div className="shared-header"><div><p>Conversation details</p><h2>{name}</h2></div><button className="shared-close" onClick={onClose} aria-label="Close shared items">×</button></div>
    <div className="shared-tabs" aria-label="Shared item type">{(['media','files','links'] as Category[]).map(tab=><button key={tab} type="button" aria-pressed={category===tab} onClick={()=>setCategory(tab)}>{tab[0].toUpperCase()+tab.slice(1)}</button>)}</div>
    <div className="shared-content" aria-live="polite">
      {!loading&&!error&&!items.length&&<p className="shared-empty">No {category} shared in this conversation yet.</p>}
      <div className={category==='media'?'shared-media-list':'shared-list'}>{items.map(item=>{
        const date=new Date(item.sent_at).toLocaleDateString();
        const url=`${API}/api/attachments/${item.id}`;
        if(category==='links')return <article className="shared-item" key={item.id}>{linksIn(item.body).map((link,index)=><a key={`${index}-${link}`} href={link} target="_blank" rel="noopener noreferrer">{link}</a>)}<small>{date}</small></article>;
        if(category==='files')return <article className="shared-item" key={item.id}><a href={url} download={item.filename||undefined}>{item.filename}</a><small>{date} · {((item.size_bytes||0)/1024/1024).toFixed(1)} MB</small></article>;
        return <article className="shared-item shared-media" key={item.id}>{item.mime_type?.startsWith('image/')?<a href={url} target="_blank" rel="noopener noreferrer"><img src={url} alt={item.filename||'Shared image'}/></a>:item.mime_type?.startsWith('video/')?<video controls preload="metadata" src={url}/>:<audio controls preload="none" src={url}/>}<a href={url} download={item.filename||undefined}>{item.filename}</a><small>{date}</small></article>;
      })}</div>
      {loading&&<p className="shared-empty" role="status">Loading shared items…</p>}
      {error&&<div className="shared-error" role="alert">{error} <button className="text-button" onClick={()=>setReload(value=>value+1)}>Try again</button></div>}
      {more&&!loading&&!error&&<button type="button" className="shared-more" onClick={()=>void loadMore()}>Load more</button>}
    </div>
  </aside>;
}
