// BACY-10 private cloud memory service. Isolated from the LiveKit token bridge.
// Incoming pairing codes are checked through a Cloudflare SERVICE BINDING to
// the existing BACY-10 token bridge; this service never stores the code.
const J=(data,status=200)=>new Response(JSON.stringify(data),{
 status,headers:{"content-type":"application/json; charset=utf-8",
 "cache-control":"no-store","x-content-type-options":"nosniff"}
});
function clean(v,n){return String(v??"").trim().slice(0,n)}
function secretLike(s){return /(?:password|passphrase|api.?key|secret|bank.?pin|cvv|one.time.password|\botp\b)/i.test(s)}
async function authorized(req,env){
 const auth=req.headers.get("Authorization")||"";
 if(!auth.startsWith("Bearer ")||auth.length>250) return false;
 try{
  const res=await env.BACY10_AUTH.fetch("https://auth.internal/token",{
   method:"POST",headers:{"Authorization":auth}});
  return res.status===201;
 }catch{return false}
}
async function body(req){const raw=await req.text();if(raw.length>50000)throw Error("payload_large");return JSON.parse(raw)}
// After an owner-requested reset, reject pre-reset cached turns and fact
// values so offline Android queues cannot resurrect wiped personal history.
// Only SHA-256 fingerprints of retired session IDs and fact values are kept.
async function resetMode(env){
  try{
    const row=await env.DB.prepare("SELECT value FROM memory_reset_control WHERE key='mode'").first();
    return String(row?.value||"");
  }catch{return ""}
}
async function sha256(value){
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,"0")).join("");
}
async function isRetired(env,kind,value){
  const hash=await sha256(value);
  const row=await env.DB.prepare(
    "SELECT 1 FROM memory_reset_replay WHERE kind=? AND hash=? LIMIT 1")
     .bind(kind,hash).first();
  return !!row;
}
export default {async fetch(req,env){
 try{
  const pathname=new URL(req.url).pathname;
  if(req.method==="GET"&&pathname==="/health"){
    return J({service:"BACY-10 owner memory",online:true});
  }
  if(!pathname.startsWith("/memory"))return J({error:"Not found"},404);
  if(!(await authorized(req,env)))return J({error:"Unauthorized"},401);
  if(req.method==="GET"&&pathname==="/memory"){
    const facts=await env.DB.prepare("SELECT key,value FROM memory_facts ORDER BY updated_at DESC LIMIT 120").all();
    const turns=await env.DB.prepare("SELECT id,session_id,role,content,created_at FROM memory_turns ORDER BY created_at DESC, rowid DESC LIMIT 80").all();
    const reset=await resetMode(env);
    const epoch=reset==="ready" ? await env.DB.prepare(
      "SELECT value FROM memory_reset_control WHERE key='epoch'").first() : null;
    return J({ok:true,facts:Object.fromEntries((facts.results||[]).map(x=>[x.key,x.value])),
      turns:(turns.results||[]).reverse(),cloud:true,
      memory_epoch:epoch?.value||""});
  }
  if(req.method==="POST"&&pathname==="/memory/turn"){
    const x=await body(req);
    const id=clean(x.id,190),session=clean(x.session_id,160),
      role=clean(x.role,20),text=clean(x.text,3000);
    if(!/^[a-zA-Z0-9:._-]{8,190}$/.test(id)||!["user","assistant"].includes(role)
      ||!text||secretLike(text))return J({error:"Invalid/sensitive turn"},400);
    const mode=await resetMode(env);
    if(mode==="resetting" || (mode==="ready" && await isRetired(env,"session",session)))
      return J({ok:true,ignored:"pre_reset_cached_turn"});
    await env.DB.prepare("INSERT OR IGNORE INTO memory_turns (id,session_id,role,content) VALUES (?,?,?,?)")
     .bind(id,session,role,text).run();
    await env.DB.prepare("DELETE FROM memory_turns WHERE id NOT IN (SELECT id FROM memory_turns ORDER BY created_at DESC,rowid DESC LIMIT 800)").run();
    return J({ok:true});
  }
  if(req.method==="POST"&&pathname==="/memory/fact"){
    const x=await body(req);
    const key=clean(x.key,65).toLowerCase(),value=clean(x.value,1300);
    if(!key||!value||secretLike(key)||secretLike(value))
      return J({error:"Invalid/sensitive fact"},400);
    const mode=await resetMode(env);
    if(mode==="resetting" || (mode==="ready" && await isRetired(env,"fact",key+String.fromCharCode(0)+value)))
      return J({ok:true,ignored:"pre_reset_cached_fact"});
    await env.DB.prepare("INSERT INTO memory_facts (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP")
     .bind(key,value).run();
    return J({ok:true});
  }
  if(req.method==="POST"&&pathname==="/memory/import"){
    const x=await body(req);
    // An old client may automatically re-import every local bundled profile
    // after an owner reset. Keep imports disabled until the updated client
    // uses explicit new owner-directed remember() calls instead.
    if(await resetMode(env))return J({ok:true,accepted:0,ignored:"owner_reset_no_old_imports"});
    const entries=Object.entries(x.facts||{}).slice(0,110);
    const queries=[];
    for(const [k,v] of entries){
      const key=clean(k,65).toLowerCase(),value=clean(v,1300);
      if(!key||!value||secretLike(key)||secretLike(value))continue;
      queries.push(env.DB.prepare("INSERT OR IGNORE INTO memory_facts (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)").bind(key,value));
    }
    if(queries.length)await env.DB.batch(queries);
    return J({ok:true,accepted:queries.length});
  }
  if(req.method==="DELETE"&&pathname==="/memory/fact"){
    const x=await body(req),key=clean(x.key,65).toLowerCase();
    if(!key)return J({error:"Missing key"},400);
    await env.DB.prepare("DELETE FROM memory_facts WHERE key=?").bind(key).run();
    return J({ok:true});
  }
  if(req.method==="DELETE"&&pathname==="/memory"){
    await env.DB.batch([
      env.DB.prepare("DELETE FROM memory_turns"),
      env.DB.prepare("DELETE FROM memory_facts")]);
    return J({ok:true,deleted:true});
  }
  return J({error:"Not found"},404);
 }catch{return J({error:"Memory temporarily unavailable"},503)}
}};