import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { Pool } from 'pg';
import { hashToken } from './core';

const database = process.env.TEST_DATABASE_URL;
const redis = process.env.TEST_REDIS_URL;
test('attachments require membership, persist, support ranges and expire', {skip: !database || !redis, timeout: 30000}, async () => {
  const schema='attachment_test_'+randomUUID().replace(/-/g,'');
  const admin=new Pool({connectionString:database});
  await admin.query(`CREATE SCHEMA ${schema}`);
  const pool=new Pool({connectionString:database,options:`-c search_path=${schema},public`});
  let child: ReturnType<typeof spawn> | undefined;
  try {
    await pool.query(await readFile('../../db/migrations/001_foundation.sql','utf8'));
    await pool.query(await readFile('../../db/migrations/002_attachments.sql','utf8'));
    const users=await pool.query("INSERT INTO users(phone,display_name) VALUES ('+12025550121','A'),('+12025550122','B'),('+12025550123','C') RETURNING id");
    const [a,b,c]=users.rows.map(x=>x.id);
    const convo=(await pool.query("INSERT INTO conversations(pair_key) VALUES ('test') RETURNING id")).rows[0].id;
    await pool.query('INSERT INTO conversation_members(conversation_id,user_id) VALUES ($1,$2),($1,$3)',[convo,a,b]);
    for (const [id,token] of [[a,'token-a'],[b,'token-b'],[c,'token-c']]) await pool.query("INSERT INTO auth_sessions(user_id,token_hash,expires_at) VALUES($1,$2,now()+interval '1 day')",[id,hashToken(token)]);
    const listener=createServer(); await new Promise<void>(resolve=>listener.listen(0,'127.0.0.1',resolve));
    const port=(listener.address() as {port:number}).port; await new Promise<void>(resolve=>listener.close(()=>resolve()));
    child=spawn(process.execPath,['dist/main.js'],{env:{...process.env,DATABASE_URL:database,PGOPTIONS:`-c search_path=${schema},public`,REDIS_URL:redis,OTP_SECRET:'test-only-otp-secret-at-least-24',WEB_ORIGIN:'http://localhost:3000',PORT:String(port),NODE_ENV:'development'},stdio:'ignore'});
    const base=`http://127.0.0.1:${port}`;
    let ready=false;
    for(let i=0;i<100;i++){try{if((await fetch(`${base}/api/health`)).ok){ready=true;break;}}catch{} await new Promise(resolve=>setTimeout(resolve,100));}
    assert.ok(ready,'API should start');
    const clientId=randomUUID(); const params=new URLSearchParams({client_id:clientId,filename:'example.pdf',type:'application/pdf'});
    const url=`${base}/api/conversations/${convo}/attachments?${params}`;
    const bytes=Buffer.from('%PDF-1.7\nexample');
    const upload=(token:string,body:Buffer)=>fetch(url,{method:'POST',headers:{origin:'http://localhost:3000',cookie:`session=${token}`,'content-type':'application/octet-stream'},body});
    assert.equal((await upload('token-c',bytes)).status,404);
    assert.equal((await upload('token-a',Buffer.from('not a pdf'))).status,400);
    assert.equal((await upload('token-a',bytes)).status,201);
    assert.equal((await upload('token-a',bytes)).status,201);
    const messages=await (await fetch(`${base}/api/conversations/${convo}/messages`,{headers:{cookie:'session=token-b'}})).json() as Array<{id:string;attachment:{available:boolean}}>;
    assert.equal(messages.length,1); assert.equal(messages[0].attachment.available,true);
    const file=`${base}/api/attachments/${messages[0].id}`;
    assert.equal((await fetch(file,{headers:{cookie:'session=token-c'}})).status,404);
    const ranged=await fetch(file,{headers:{cookie:'session=token-b',range:'bytes=0-3'}});
    assert.equal(ranged.status,206); assert.equal(await ranged.text(),'%PDF');
    const shared=(type:string,token='token-b',before?:string)=>fetch(`${base}/api/conversations/${convo}/shared?${new URLSearchParams({type,...(before?{before}:{})})}`,{headers:{cookie:`session=${token}`}});
    assert.equal((await shared('files','token-c')).status,404);
    const files=await (await shared('files')).json() as {items:Array<{id:string}>};
    assert.equal(files.items.length,1); assert.equal(files.items[0].id,messages[0].id);
    const imageParams=new URLSearchParams({client_id:randomUUID(),filename:'photo.png',type:'image/png'});
    assert.equal((await fetch(`${base}/api/conversations/${convo}/attachments?${imageParams}`,{method:'POST',headers:{origin:'http://localhost:3000',cookie:'session=token-a','content-type':'application/octet-stream'},body:Buffer.from('89504e470d0a1a0a00000000','hex')})).status,201);
    const media=await (await shared('media')).json() as {items:Array<{filename:string}>};
    assert.equal(media.items.length,1); assert.equal(media.items[0].filename,'photo.png');
    await pool.query("INSERT INTO messages(conversation_id,sender_id,client_id,body) SELECT $1,$2,gen_random_uuid(),'Visit https://example.com/' || n FROM generate_series(1,52) n",[convo,a]);
    await pool.query("INSERT INTO messages(conversation_id,sender_id,client_id,body,deleted_at) VALUES($1,$2,gen_random_uuid(),'https://deleted.example',now())",[convo,a]);
    const first=await (await shared('links')).json() as {items:Array<{id:string}>;has_more:boolean};
    assert.equal(first.items.length,50); assert.equal(first.has_more,true);
    const second=await (await shared('links','token-b',first.items[49].id)).json() as {items:Array<{id:string}>;has_more:boolean};
    assert.equal(second.items.length,2); assert.equal(second.has_more,false);
    assert.equal(new Set([...first.items,...second.items].map(item=>item.id)).size,52);
    await pool.query("UPDATE attachments SET expires_at=now()-interval '1 second'");
    assert.equal((await fetch(file,{headers:{cookie:'session=token-b'}})).status,404);
    assert.equal(((await (await shared('files')).json()) as {items:unknown[]}).items.length,0);
    assert.equal(((await (await shared('media')).json()) as {items:unknown[]}).items.length,0);
  } finally {
    if(child){child.kill(); await new Promise<void>(resolve=>child!.once('exit',()=>resolve()));}
    await pool.end(); await admin.query(`DROP SCHEMA ${schema} CASCADE`); await admin.end();
  }
});
