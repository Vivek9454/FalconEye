const S = {
  primary: '#0F9D58', accent: '#00B5D8', apiLocal: 'http://localhost:3000', apiRemote: 'https://cam.falconeye.website'
}

async function pickServer(){
  try{ const r = await fetch(S.apiLocal+'/mobile/status'); if(r.ok) return S.apiLocal; }catch(e){}
  return S.apiRemote
}

function el(tag, cls, html){ const e=document.createElement(tag); if(cls) e.className=cls; if(html) e.innerHTML=html; return e }

function toast(msg){ const t=el('div','toast',msg); document.body.appendChild(t); setTimeout(()=>t.remove(),1800) }

async function Live(server){
  const root = el('div','screen');
  const tabs = el('div','tabs');
  ;['Live','Clips','Status'].forEach((n,i)=>{ const b=el('div','tab'+(i==0?' active':''),n); b.onclick=()=>route(n.toLowerCase()); tabs.appendChild(b) })
  root.appendChild(tabs)

  const card = el('div','glass'); card.style.padding='8px';
  const img = el('img'); card.appendChild(img); root.appendChild(card)
  const badges = el('div','row'); badges.appendChild(el('span','badge','AI optimized')); root.appendChild(badges)
  let t=0; setInterval(()=>{ img.src=`${server}/camera/snapshot/cam1?t=${Date.now()}`; },1500)
  return root
}

async function Clips(server){
  const root = el('div','screen');
  const tabs = el('div','tabs');
  ;['Live','Clips','Status'].forEach((n,i)=>{ const b=el('div','tab'+(i==1?' active':''),n); b.onclick=()=>route(n.toLowerCase()); tabs.appendChild(b) })
  root.appendChild(tabs)

  const grid = el('div','grid'); root.appendChild(grid)
  const md = await (await fetch(server+'/clips')).json();
  Object.keys(md).sort().reverse().slice(0,20).forEach(name=>{
    const th = el('div','thumb glass');
    const img = el('img'); img.src = `${server}/clips/${name}?thumb=1`; th.appendChild(img)
    const meta = el('div','meta'); meta.appendChild(el('span','badge','Clip')); th.appendChild(meta)
    th.onclick=()=>route('player', {name});
    grid.appendChild(th)
  })
  return root
}

async function Status(server){
  const root = el('div','screen');
  const tabs = el('div','tabs');
  ;['Live','Clips','Status'].forEach((n,i)=>{ const b=el('div','tab'+(i==2?' active':''),n); b.onclick=()=>route(n.toLowerCase()); tabs.appendChild(b) })
  root.appendChild(tabs)
  const card = el('div','glass'); card.style.padding='16px';
  const sys = await (await fetch(server+'/system/status')).json();
  card.innerHTML = `<div class="row"><span class="badge">Device: ${sys.device}</span>${sys.gpu?`<span class=badge>GPU: ${sys.gpu}</span>`:''}</div>`
  root.appendChild(card)
  return root
}

async function Player(server, {name}){
  const root = el('div','screen');
  const card = el('div','glass'); card.style.padding='8px';
  const video = el('video'); video.controls=true; video.src=`${server}/clips/${name}`; video.style.width='100%'; card.appendChild(video)
  root.appendChild(card)
  return root
}

let SERVER='';
async function route(screen, params={}){
  if(!SERVER) SERVER = await pickServer();
  const app=document.getElementById('app'); app.innerHTML='';
  if(screen==='clips') app.appendChild(await Clips(SERVER));
  else if(screen==='status') app.appendChild(await Status(SERVER));
  else if(screen==='player') app.appendChild(await Player(SERVER, params));
  else app.appendChild(await Live(SERVER));
}

route('live');

