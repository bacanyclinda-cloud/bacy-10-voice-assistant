// BACY-10 private cloud memory service. Isolated from the LiveKit token bridge.
// Incoming pairing codes are checked through a Cloudflare SERVICE BINDING to
// the existing BACY-10 token bridge; this service never stores the code.
const J=(data,status=200)=>new Response(JSON.stringify(data),{
 status,headers:{"content-type":"application/json; charset=utf-8",
 "cache-control":"no-store","x-content-type-options":"nosniff"}
});
function clean(v,n){return String(v??"").trim().slice(0,n)}
function luhnValid(value){
 const digits=String(value).replace(/\D/g,"");
 if(digits.length<13||digits.length>19)return false;
 let sum=0,alternate=false;
 for(let i=digits.length-1;i>=0;i--){
  let n=Number(digits[i]);
  if(alternate){n*=2;if(n>9)n-=9;}
  sum+=n;alternate=!alternate;
 }
 return sum%10===0;
}
export function isSensitiveMemoryContent(value){
 const s=String(value??"");
 if(/(?:password|passphrase|api.?key|secret|bank.?pin|cvv|one.time.password|\botp\b)/i.test(s))return true;
 if(/-----BEGIN (?:RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----/i.test(s))return true;
 if(/\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\b|\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bAIza[0-9A-Za-z_-]{30,}\b|\bAKIA[0-9A-Z]{16}\b/i.test(s))return true;
 if(/\bBearer\s+[A-Za-z0-9._~+\/-]{20,}/i.test(s))return true;
 if(/\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/.test(s))return true;
 const candidates=s.match(/(?:\d[ -]?){13,19}/g)||[];
 return candidates.some(luhnValid);
}
const secretLike=isSensitiveMemoryContent;
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
async function memoryEpoch(env){
  try{
    const row=await env.DB.prepare("SELECT value FROM memory_reset_control WHERE key='epoch'").first();
    return String(row?.value||"bacy-initial");
  }catch{return "bacy-initial"}
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
  if(req.method==="POST"&&pathname==="/memory/reset-owner"){
    // This operation can only be called with the owner's pairing-code bearer
    // and explicit typed confirmation. Never expose an anonymous reset URL.
    const x=await body(req);
    if(x.confirm!=="RESET MY BACY-10 MEMORY")return J({error:"Confirmation required"},400);
    const raw=x.facts;
    if(!raw||typeof raw!=="object"||Array.isArray(raw))return J({error:"Missing replacement preferences"},400);
    const allowed=new Set(["owner_behavior_preferences","owner_workflow_preferences","owner_voice_style"]);
    const entries=Object.entries(raw);
    if(entries.length!==3 || entries.some(([k,v])=>!allowed.has(k) ||
       typeof v!=="string" || v.length<30 || v.length>1300 || secretLike(v)))
       return J({error:"Invalid replacement preferences"},400);
    const oldMode=await resetMode(env);
    try{
      // Stop any pre-reset phone queues from writing during this transition.
      await env.DB.prepare(
        "INSERT INTO memory_reset_control(key,value) VALUES('mode','resetting') "+
        "ON CONFLICT(key) DO UPDATE SET value='resetting'").run();
      const sessions=await env.DB.prepare("SELECT DISTINCT session_id FROM memory_turns").all();
      const priorFacts=await env.DB.prepare("SELECT key,value FROM memory_facts").all();
      const turnCount=await env.DB.prepare("SELECT COUNT(*) AS n FROM memory_turns").first();
      const oldPairs=[];
      for(const r of sessions.results||[])
        oldPairs.push(["session",await sha256(String(r.session_id??""))]);
      for(const r of priorFacts.results||[])
        oldPairs.push(["fact",await sha256(String(r.key)+String.fromCharCode(0)+String(r.value))]);
      // Store no old conversation text or old personal facts, only hashes to
      // prevent replay by other offline copies of the app.
      for(let i=0;i<oldPairs.length;i+=20){
        const batch=oldPairs.slice(i,i+20).map(([kind,hash])=>
          env.DB.prepare("INSERT OR IGNORE INTO memory_reset_replay(kind,hash) VALUES (?,?)")
            .bind(kind,hash));
        if(batch.length)await env.DB.batch(batch);
      }
      const epoch="bacy-reset-"+Date.now().toString(36);
      const statements=[
        env.DB.prepare("DELETE FROM memory_turns"),
        env.DB.prepare("DELETE FROM memory_facts"),
        ...entries.map(([k,v])=>env.DB.prepare(
          "INSERT INTO memory_facts(key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)")
           .bind(k,v.trim())),
        env.DB.prepare("INSERT INTO memory_reset_control(key,value) VALUES('epoch',?) "+
          "ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(epoch),
        env.DB.prepare("INSERT INTO memory_reset_control(key,value) VALUES('mode','ready') "+
          "ON CONFLICT(key) DO UPDATE SET value='ready'")
      ];
      await env.DB.batch(statements);
      return J({ok:true,reset:true,memory_epoch:epoch,
        previous_turns_deleted:turnCount?.n||0,previous_facts_deleted:(priorFacts.results||[]).length,
        saved_preferences:entries.map(([k])=>k)});
    }catch(err){
      // Recovery is possible even if the remote service briefly fails.
      await env.DB.prepare("DELETE FROM memory_reset_control WHERE key='mode'").run().catch(()=>{});
      if(oldMode)await env.DB.prepare(
        "INSERT INTO memory_reset_control(key,value) VALUES('mode',?)").bind(oldMode).run().catch(()=>{});
      return J({error:"Reset failed; check memory before retrying"},503);
    }
  }
  if(req.method==="GET"&&pathname==="/memory"){
    const facts=await env.DB.prepare("SELECT key,value FROM memory_facts ORDER BY updated_at DESC LIMIT 120").all();
    const turns=await env.DB.prepare("SELECT id,session_id,role,content,created_at FROM memory_turns ORDER BY created_at DESC, rowid DESC LIMIT 80").all();
    const reset=await resetMode(env);
    const epoch=reset==="resetting" ? "bacy-reset-pending" : await memoryEpoch(env);
    return J({ok:true,facts:Object.fromEntries((facts.results||[]).map(x=>[x.key,x.value])),
      turns:(turns.results||[]).reverse(),cloud:true,memory_epoch:epoch});
  }
  if(req.method==="POST"&&pathname==="/memory/turn"){
    const x=await body(req);
    const id=clean(x.id,190),session=clean(x.session_id,160),
      role=clean(x.role,20),text=clean(x.text,3000);
    if(!/^[a-zA-Z0-9:._-]{8,190}$/.test(id)||!["user","assistant"].includes(role)
      ||!text||secretLike(text))return J({error:"Invalid/sensitive turn"},400);
    const mode=await resetMode(env);
    const epoch=await memoryEpoch(env);
    if(String(x.memory_epoch??"bacy-initial")!==epoch)
      return J({ok:true,ignored:"stale_memory_epoch"});
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
    const epoch=await memoryEpoch(env);
    if(String(x.memory_epoch??"bacy-initial")!==epoch)
      return J({ok:true,ignored:"stale_memory_epoch"});
    if(mode==="resetting" || (mode==="ready" &&
        await isRetired(env,"fact",key+String.fromCharCode(0)+value) && x.allow_readd!==true))
      return J({ok:true,ignored:"pre_reset_cached_fact"});
    if(value==="__BACY10_DELETED__"){
      const existing=await env.DB.prepare("SELECT value FROM memory_facts WHERE key=?").bind(key).first();
      if(existing?.value!==undefined && existing.value!=="__BACY10_DELETED__"){
        const retired=await sha256(key+String.fromCharCode(0)+String(existing.value));
        await env.DB.prepare("INSERT OR IGNORE INTO memory_reset_replay(kind,hash) VALUES ('fact',?)")
          .bind(retired).run();
      }
    }
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
    const existing=await env.DB.prepare("SELECT value FROM memory_facts WHERE key=?").bind(key).first();
    if(existing?.value!==undefined){
      const hash=await sha256(key+String.fromCharCode(0)+String(existing.value));
      await env.DB.prepare("INSERT OR IGNORE INTO memory_reset_replay(kind,hash) VALUES ('fact',?)")
        .bind(hash).run();
    }
    await env.DB.prepare("DELETE FROM memory_facts WHERE key=?").bind(key).run();
    return J({ok:true});
  }
  if(req.method==="DELETE"&&pathname==="/memory"){
    const oldMode=await resetMode(env);
    try{
      await env.DB.prepare(
        "INSERT INTO memory_reset_control(key,value) VALUES('mode','resetting') "+
        "ON CONFLICT(key) DO UPDATE SET value='resetting'").run();
      const sessions=await env.DB.prepare("SELECT DISTINCT session_id FROM memory_turns").all();
      const priorFacts=await env.DB.prepare("SELECT key,value FROM memory_facts").all();
      const turnCount=await env.DB.prepare("SELECT COUNT(*) AS n FROM memory_turns").first();
      const oldPairs=[];
      for(const row of sessions.results||[])
        oldPairs.push(["session",await sha256(String(row.session_id??""))]);
      for(const row of priorFacts.results||[])
        oldPairs.push(["fact",await sha256(String(row.key)+String.fromCharCode(0)+String(row.value))]);
      // Keep hashes only, so offline copies of old turns/facts cannot restore
      // deleted memory after the owner has reset it.
      for(let i=0;i<oldPairs.length;i+=20){
        const batch=oldPairs.slice(i,i+20).map(([kind,hash])=>
          env.DB.prepare("INSERT OR IGNORE INTO memory_reset_replay(kind,hash) VALUES (?,?)")
            .bind(kind,hash));
        if(batch.length)await env.DB.batch(batch);
      }
      const epoch="bacy-reset-"+Date.now().toString(36);
      await env.DB.batch([
        env.DB.prepare("DELETE FROM memory_turns"),
        env.DB.prepare("DELETE FROM memory_facts"),
        env.DB.prepare("INSERT INTO memory_reset_control(key,value) VALUES('epoch',?) "+
          "ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(epoch),
        env.DB.prepare("INSERT INTO memory_reset_control(key,value) VALUES('mode','ready') "+
          "ON CONFLICT(key) DO UPDATE SET value='ready'")
      ]);
      return J({ok:true,deleted:true,memory_epoch:epoch,
        previous_turns_deleted:turnCount?.n||0,
        previous_facts_deleted:(priorFacts.results||[]).length});
    }catch(err){
      await env.DB.prepare("DELETE FROM memory_reset_control WHERE key='mode'").run().catch(()=>{});
      if(oldMode)await env.DB.prepare(
        "INSERT INTO memory_reset_control(key,value) VALUES('mode',?)")
        .bind(oldMode).run().catch(()=>{});
      return J({error:"Memory reset failed; check connection before retrying"},503);
    }
  }
  return J({error:"Not found"},404);
 }catch{return J({error:"Memory temporarily unavailable"},503)}
}};