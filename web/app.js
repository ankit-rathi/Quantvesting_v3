const state = { run: null, accessKey: sessionStorage.getItem('qv_access_key') || '' };
const $ = id => document.getElementById(id);

function headers(){ return state.accessKey ? {'X-QV-Access-Key': state.accessKey, 'Content-Type':'application/json'} : {'Content-Type':'application/json'}; }
async function api(path, options={}){
  const opts = {...options, headers:{...(options.headers||{}), ...headers()}};
  const res = await fetch(path, opts);
  const data = await res.json().catch(()=>({detail:res.statusText}));
  if(!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function money(v){
  if(v===null || v===undefined || Number.isNaN(Number(v))) return 'N/A';
  const n=Number(v), a=Math.abs(n);
  if(a>=1e7) return `${(n/1e7).toFixed(2)} C`;
  if(a>=1e5) return `${(n/1e5).toFixed(2)} L`;
  if(a>=1e3) return `${(n/1e3).toFixed(2)} K`;
  return n.toFixed(2);
}
function pct(v){ if(v===null||v===undefined||Number.isNaN(Number(v))) return 'N/A'; return `${Number(v).toFixed(2)}%`; }
function setStatus(text, cls=''){ const el=$('runStatus'); el.textContent=text; el.className=cls; }
function showError(e){ $('error').textContent=e.message||String(e); $('error').classList.remove('hidden'); setStatus('Error','status-error'); }
function clearError(){ $('error').classList.add('hidden'); }

async function loadPortfolios(){
  try{
    const data=await api('/api/v1/portfolios');
    const sel=$('portfolioSelect'); sel.innerHTML='';
    data.portfolios.forEach(id=>{const o=document.createElement('option');o.value=id;o.textContent=id;sel.appendChild(o)});
    if(data.portfolios.includes(data.default)) sel.value=data.default;
    else if(data.portfolios.length) sel.value=data.portfolios[0];
  }catch(e){
    // If access is configured, show the access prompt rather than failing silently.
    if(e.message.includes('access key')) $('accessModal').classList.remove('hidden'); else showError(e);
  }
}

async function runAnalysis(){
  clearError(); setStatus('Running…','status-running'); $('runBtn').disabled=true;
  try{
    const data=await api('/api/v1/runs',{method:'POST',body:JSON.stringify({
      portfolio_id:$('portfolioSelect').value || 'ankit',
      refresh_screener:$('refreshScreener').checked,
      eod:$('eodRun').checked
    })});
    state.run=data; renderAll(data); setStatus(`Completed · ${data.run_id}`,'status-ok');
  }catch(e){showError(e)} finally{$('runBtn').disabled=false;}
}

function renderAll(d){
  const s=d.summary||{}; $('deployed').textContent=money(s.deployed ?? s.initial_investment); $('current').textContent=money(s.current); $('xirr').textContent=s.cagr_xirr==null?'N/A':pct(s.cagr_xirr); $('runId').textContent=d.run_id||'—'; $('runDate').textContent=s.run_datetime||'—';
  $('todayPnl').textContent=`${money(s.today_pnl_amount)} (${pct(s.today_pnl_percentage)})`;
  $('currentPnl').textContent=`${money(s.curr_pnl_amount)} (${pct(s.curr_pnl_percentage)})`;
  $('prospectCount').textContent=(d.prospects||[]).length; $('rotationCount').textContent=(d.rotation||[]).length;
  renderTable('prospectsTable',d.prospects||[],$('prospectSearch').value); renderTable('portfolioTable',d.portfolio||[],$('portfolioSearch').value);
  renderDecisions(d); renderDonut(d.portfolio||[]);
}

function renderTable(id, rows, filter=''){
  const table=$(id); table.innerHTML=''; if(!rows.length){table.innerHTML='<tbody><tr><td>No data</td></tr></tbody>';return;}
  const keys=Object.keys(rows[0]); const q=filter.trim().toLowerCase(); const filtered=q?rows.filter(r=>keys.some(k=>String(r[k]??'').toLowerCase().includes(q))):rows;
  const thead=document.createElement('thead'), tr=document.createElement('tr'); keys.forEach(k=>{const th=document.createElement('th');th.textContent=k;tr.appendChild(th)});thead.appendChild(tr);table.appendChild(thead);
  const tbody=document.createElement('tbody'); filtered.forEach(r=>{const row=document.createElement('tr');keys.forEach(k=>{const td=document.createElement('td');let v=r[k]; if(['FTT','Current','Current P/L','FTT Amt','AvgCost'].includes(k)) v=money(v); else if(k.includes('%')) v=pct(v); td.textContent=v==null?'—':v;row.appendChild(td)});tbody.appendChild(row)});table.appendChild(tbody);
}
function item(title, action, extra=''){ const d=document.createElement('div');d.className='decision-item';d.innerHTML=`<strong>${title||'—'}</strong><span class="badge">${action||'—'}</span>${extra?`<div class="muted" style="margin-top:5px">${extra}</div>`:''}`;return d; }
function renderDecisions(d){
  $('prospectActions').innerHTML=''; (d.prospect_actions||[]).filter(x=>x.Action&&x.Action!=='WATCHLIST').forEach(x=>$('prospectActions').appendChild(item(x.Symbol,x.Action,`CumlRnk: ${x.CumlRnk??'—'} · FTT: ${money(x.FTT)}`)));
  if(!$('prospectActions').children.length)$('prospectActions').innerHTML='<div class="muted">No buy candidates in top 10.</div>';
  $('portfolioActions').innerHTML=''; (d.portfolio_actions||[]).forEach(x=>$('portfolioActions').appendChild(item(x.Symbol,x.Action,`FTT Amt: ${money(x['FTT Amt'])} · RRR Ind: ${x['RRR Ind']??'—'}`)));
  if(!$('portfolioActions').children.length)$('portfolioActions').innerHTML='<div class="muted">No portfolio actions.</div>';
  $('rotationActions').innerHTML=''; (d.rotation||[]).forEach(x=>$('rotationActions').appendChild(item(x.Symbol,x.Action,`Alternative: ${x.AlternativeSymbol||'—'} · Rank: ${x.AlternativeCumlRnk??'—'}`)));
  if(!$('rotationActions').children.length)$('rotationActions').innerHTML='<div class="muted">No capital rotation candidates.</div>';
  $('attention').innerHTML='';
  const candidates=[...(d.portfolio_actions||[]).filter(x=>x.Action&&x.Action!=='HOLD'),...(d.prospect_actions||[]).filter(x=>x.Action==='BUY_CANDIDATE')].slice(0,8);
  candidates.forEach(x=>$('attention').appendChild(item(x.Symbol,x.Action)));
  if(!$('attention').children.length)$('attention').innerHTML='<div class="muted">No immediate signals.</div>';
}
function renderDonut(rows){
  const groups={}; rows.forEach(r=>{const c=r.Category||'Unclassified';const v=Number(r.Current)||0;groups[c]=(groups[c]||0)+Math.max(v,0)}); const entries=Object.entries(groups).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]); const total=entries.reduce((a,x)=>a+x[1],0); if(!total)return;
  let start=0; const stops=[]; const colors=['#2563eb','#7c3aed','#059669','#d97706','#dc2626','#0891b2','#db2777','#64748b']; $('legend').innerHTML=''; entries.forEach(([k,v],i)=>{const end=start+v/total*360;stops.push(`${colors[i%colors.length]} ${start}deg ${end}deg`);const row=document.createElement('div');row.className='legend-row';row.innerHTML=`<span class="dot" style="background:${colors[i%colors.length]}"></span>${k}: ${((v/total)*100).toFixed(1)}%`;$('legend').appendChild(row);start=end});$('donut').style.background=`conic-gradient(${stops.join(',')})`;
}

$('runBtn').addEventListener('click',runAnalysis); $('settingsBtn').addEventListener('click',()=>{$('accessKey').value=state.accessKey;$('accessModal').classList.remove('hidden')}); $('cancelAccess').addEventListener('click',()=>$('accessModal').classList.add('hidden')); $('saveAccess').addEventListener('click',async()=>{state.accessKey=$('accessKey').value.trim();sessionStorage.setItem('qv_access_key',state.accessKey);$('accessModal').classList.add('hidden');await loadPortfolios()}); $('prospectSearch').addEventListener('input',()=>{if(state.run)renderTable('prospectsTable',state.run.prospects,$('prospectSearch').value)}); $('portfolioSearch').addEventListener('input',()=>{if(state.run)renderTable('portfolioTable',state.run.portfolio,$('portfolioSearch').value)});
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$(b.dataset.tab).classList.add('active')}));
loadPortfolios().then(()=>{ if($('portfolioSelect').options.length) runAnalysis(); });
