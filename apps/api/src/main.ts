import 'reflect-metadata';
import { BadRequestException, Body, Controller, Get, HttpException, Injectable, Module, Param, Post, Query, Req, Res, UnauthorizedException } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { WebSocketGateway, WebSocketServer, OnGatewayConnection } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Request, Response } from 'express';
import cookieParser from 'cookie-parser';
import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import { sql } from 'drizzle-orm';
import Redis from 'ioredis';
import { z, ZodError } from 'zod';
import { codeHash, hashToken, newCode, newToken, normalizePhone, safeEqual } from './core';
import { issueVerification, lockVerification } from './verification';

const origin = process.env.WEB_ORIGIN || 'http://localhost:3000';
const secret = process.env.OTP_SECRET;
if (!secret || secret.length < 24) throw new Error('OTP_SECRET must be at least 24 characters');
if (process.env.NODE_ENV === 'production') throw new Error('The development OTP provider must not run in production');
const otpSecret: string = secret;
const pool = new Pool({ connectionString: process.env.DATABASE_URL || 'postgres://app:local_password@localhost:5432/messaging', max: 10 });
const db = drizzle(pool);
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', { maxRetriesPerRequest: 1 });
let redisUnavailable = false;
redis.on('error', () => { if (!redisUnavailable) console.error(JSON.stringify({event:'redis_unavailable'})); redisUnavailable = true; });
redis.on('ready', () => { if (redisUnavailable) console.log(JSON.stringify({event:'redis_recovered'})); redisUnavailable = false; });
const uuid = z.string().uuid();
const phoneInput = z.string().min(5).max(30);
const purposeInput = z.enum(['register', 'signin']);
function phone(value: string) { try { return normalizePhone(value); } catch { throw new BadRequestException('Enter a valid international phone number beginning with +.'); } }
function parse<T>(schema: z.ZodType<T>, value: unknown): T { try { return schema.parse(value); } catch (e) { if (e instanceof ZodError) throw new BadRequestException('Invalid request.'); throw e; } }
async function limit(key: string, count: number, seconds: number) {
  let result;
  try { result = await redis.multi().incr(key).expire(key, seconds, 'NX').exec(); }
  catch { throw new HttpException('Rate limiter unavailable.', 503); }
  if (!result || result.some(([err]) => err)) throw new HttpException('Rate limiter unavailable.', 503);
  if (Number(result[0][1]) > count) throw new HttpException('Too many attempts. Try again later.', 429);
}

@Injectable()
class Store {
  async user(token?: string) {
    if (!token) throw new UnauthorizedException();
    const result = await pool.query('SELECT u.id,u.display_name FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=$1 AND s.revoked_at IS NULL AND s.expires_at>now()', [hashToken(token)]);
    if (!result.rows[0]) throw new UnauthorizedException();
    return result.rows[0] as {id:string;display_name:string};
  }
  async member(userId: string, conversationId: string) {
    const r = await pool.query('SELECT 1 FROM conversation_members WHERE user_id=$1 AND conversation_id=$2', [userId, conversationId]);
    if (!r.rowCount) throw new HttpException('Conversation unavailable.', 404);
  }
}

@WebSocketGateway({ cors: { origin, credentials: true } })
class Events implements OnGatewayConnection {
  @WebSocketServer() server!: Server;
  constructor(private readonly store: Store) {}
  async handleConnection(client: Socket) {
    try {
      if (client.handshake.headers.origin !== origin) throw new Error('Invalid origin');
      const cookies = Object.fromEntries((client.handshake.headers.cookie || '').split(';').map(x => x.trim().split('=')));
      const user = await this.store.user(cookies.session);
      client.join(`user:${user.id}`);
    } catch { client.disconnect(true); }
  }
  async changed(conversation: string) {
    const r = await pool.query('SELECT user_id FROM conversation_members WHERE conversation_id=$1', [conversation]);
    for (const row of r.rows) this.server.to(`user:${row.user_id}`).emit('conversation:changed', {conversation_id: conversation});
  }
}

@Controller('api')
class Api {
  constructor(private readonly store: Store, private readonly events: Events) {}
  @Get('health') async health() { await db.execute(sql`SELECT 1`); await redis.ping(); return {status:'ok'}; }

  @Post('auth/request-code') async requestCode(@Body() input: unknown, @Req() req: Request) {
    const data = parse(z.object({phone:phoneInput,purpose:purposeInput}), input); const number = phone(data.phone);
    await limit(`otp:ip:${req.ip}`, 20, 3600); await limit(`otp:phone:${hashToken(number)}`, 5, 3600);
    const code = newCode();
    await issueVerification(pool, number, data.purpose, codeHash(number,data.purpose,code,otpSecret));
    console.log(JSON.stringify({event:'development_otp',phone:number,purpose:data.purpose,code}));
    return {message:'If the number is eligible, a verification code has been sent.'};
  }

  @Post('auth/verify') async verify(@Body() input: unknown, @Res({passthrough:true}) res: Response) {
    const data = parse(z.object({phone:phoneInput,purpose:purposeInput,code:z.string().regex(/^\d{6}$/),display_name:z.string().trim().min(1).max(80).optional()}), input);
    const number = phone(data.phone); await limit(`verify:${hashToken(number)}`, 12, 3600);
    if (data.purpose === 'register' && !data.display_name) throw new BadRequestException('Display name is required.');
    const client = await pool.connect(); let userId: string | undefined;
    try {
      await client.query('BEGIN');
      await lockVerification(client, number, data.purpose);
      const result = await client.query('SELECT * FROM phone_verifications WHERE phone=$1 AND purpose=$2 AND consumed_at IS NULL ORDER BY created_at DESC LIMIT 1 FOR UPDATE', [number,data.purpose]);
      const row = result.rows[0];
      if (!row || row.attempts >= 5 || new Date(row.expires_at).getTime() <= Date.now()) { await client.query('ROLLBACK'); throw new BadRequestException('Code is invalid or expired.'); }
      await client.query('UPDATE phone_verifications SET attempts=attempts+1 WHERE id=$1',[row.id]);
      if (!safeEqual(row.code_hash,codeHash(number,data.purpose,data.code,otpSecret))) { await client.query('COMMIT'); throw new BadRequestException('Code is invalid or expired.'); }
      await client.query('UPDATE phone_verifications SET consumed_at=now() WHERE id=$1',[row.id]);
      if (data.purpose === 'register') {
        await client.query('INSERT INTO users(phone,display_name) VALUES($1,$2) ON CONFLICT(phone) DO NOTHING', [number,data.display_name]);
      } else {
        const u = await client.query('SELECT id FROM users WHERE phone=$1',[number]); userId = u.rows[0]?.id;
      }
      await client.query('COMMIT');
    } catch (err) { try { await client.query('ROLLBACK'); } catch {} throw err; } finally { client.release(); }
    if (data.purpose === 'register') return {message:'Registration verification complete. Request a new code to sign in.'};
    if (!userId) throw new UnauthorizedException('Unable to sign in.');
    const token = newToken();
    await pool.query("INSERT INTO auth_sessions(user_id,token_hash,expires_at) VALUES($1,$2,now()+interval '7 days')", [userId,hashToken(token)]);
    res.cookie('session',token,{httpOnly:true,sameSite:'strict',secure:false,path:'/',maxAge:7*24*3600*1000});
    return {message:'Signed in.'};
  }
  @Get('auth/me') async me(@Req() req: Request) { return this.store.user(req.cookies?.session); }
  @Post('auth/logout') async logout(@Req() req: Request,@Res({passthrough:true}) res: Response) {
    const token = req.cookies?.session;
    if (token) { const session = await pool.query('UPDATE auth_sessions SET revoked_at=now() WHERE token_hash=$1 RETURNING user_id',[hashToken(token)]); if(session.rows[0]) this.events.server.in(`user:${session.rows[0].user_id}`).disconnectSockets(true); }
    res.clearCookie('session',{path:'/'}); return {ok:true};
  }
  @Post('contacts') async addContact(@Req() req: Request,@Body() input: unknown) {
    const user = await this.store.user(req.cookies?.session); const data = parse(z.object({phone:phoneInput}),input); const number = phone(data.phone);
    await limit(`contact:${user.id}`, 30, 3600);
    await pool.query('INSERT INTO contacts(owner_id,phone) VALUES($1,$2) ON CONFLICT DO NOTHING',[user.id,number]);
    return {message:'Contact saved. A conversation appears when both people have added each other.'};
  }
  @Get('conversations') async conversations(@Req() req: Request) {
    const user = await this.store.user(req.cookies?.session);
    const matches = await pool.query(`SELECT other.id FROM users me JOIN contacts mine ON mine.owner_id=me.id JOIN users other ON other.phone=mine.phone JOIN contacts theirs ON theirs.owner_id=other.id AND theirs.phone=me.phone WHERE me.id=$1 AND other.id<>me.id`,[user.id]);
    for (const match of matches.rows) {
      const pair = [user.id,match.id].sort().join(':');
      const c = await pool.query('INSERT INTO conversations(pair_key) VALUES($1) ON CONFLICT(pair_key) DO UPDATE SET pair_key=EXCLUDED.pair_key RETURNING id',[pair]);
      await pool.query('INSERT INTO conversation_members(conversation_id,user_id) VALUES($1,$2),($1,$3) ON CONFLICT DO NOTHING',[c.rows[0].id,user.id,match.id]);
    }
    const r = await pool.query(`SELECT c.id,u.display_name, (SELECT body FROM messages WHERE conversation_id=c.id AND deleted_at IS NULL ORDER BY sent_at DESC,id DESC LIMIT 1) AS last_message FROM conversations c JOIN conversation_members cm ON cm.conversation_id=c.id AND cm.user_id=$1 JOIN conversation_members peer ON peer.conversation_id=c.id AND peer.user_id<>$1 JOIN users u ON u.id=peer.user_id ORDER BY c.created_at DESC`,[user.id]);
    return r.rows;
  }
  @Get('conversations/:id/messages') async messages(@Req() req:Request,@Param('id') id:string,@Query('before') before?:string) {
    const user=await this.store.user(req.cookies?.session); parse(uuid,id); if(before) parse(uuid,before); await this.store.member(user.id,id);
    const r=await pool.query(`SELECT m.id,m.client_id,m.sender_id,m.body,m.sent_at,m.edited_at,m.deleted_at, r.delivered_at,r.read_at FROM messages m LEFT JOIN message_receipts r ON r.message_id=m.id AND r.user_id<>m.sender_id WHERE m.conversation_id=$1 AND ($2::uuid IS NULL OR (m.sent_at,m.id)<(SELECT sent_at,id FROM messages WHERE id=$2 AND conversation_id=$1)) ORDER BY m.sent_at DESC,m.id DESC LIMIT 50`,[id,before||null]);
    return r.rows.reverse();
  }
  @Post('conversations/:id/messages') async send(@Req() req:Request,@Param('id') id:string,@Body() input:unknown) {
    const user=await this.store.user(req.cookies?.session); parse(uuid,id); await this.store.member(user.id,id);
    const data=parse(z.object({client_id:uuid,body:z.string().trim().min(1).max(5000)}),input);
    const r=await pool.query('INSERT INTO messages(conversation_id,sender_id,client_id,body) VALUES($1,$2,$3,$4) ON CONFLICT(sender_id,client_id) DO NOTHING RETURNING *',[id,user.id,data.client_id,data.body]);
    const m=r.rows[0] || (await pool.query('SELECT * FROM messages WHERE sender_id=$1 AND client_id=$2',[user.id,data.client_id])).rows[0];
    if(m.conversation_id!==id || m.body!==data.body) throw new HttpException('Client message ID already used.',409);
    await this.events.changed(id); return m;
  }
  @Post('conversations/:id/read') async read(@Req() req:Request,@Param('id') id:string) {
    const user=await this.store.user(req.cookies?.session); parse(uuid,id); await this.store.member(user.id,id);
    const changed=await pool.query(`INSERT INTO message_receipts(message_id,user_id,delivered_at,read_at) SELECT id,$2,now(),now() FROM messages WHERE conversation_id=$1 AND sender_id<>$2 ON CONFLICT(message_id,user_id) DO UPDATE SET delivered_at=COALESCE(message_receipts.delivered_at,now()),read_at=COALESCE(message_receipts.read_at,now()) WHERE message_receipts.read_at IS NULL`,[id,user.id]);
    if(changed.rowCount) await this.events.changed(id); return {ok:true};
  }
}
@Module({controllers:[Api],providers:[Store,Events]}) class AppModule {}
async function bootstrap() {
  const app=await NestFactory.create(AppModule,{bodyParser:true});
  app.use(cookieParser());
  app.enableCors({origin,credentials:true});
  app.use((req:Request,res:Response,next:()=>void)=>{ if(!['GET','HEAD','OPTIONS'].includes(req.method) && req.headers.origin!==origin) { res.status(403).json({message:'Invalid origin'}); return; } next(); });
  await app.listen(3001,'0.0.0.0');
}
bootstrap();
