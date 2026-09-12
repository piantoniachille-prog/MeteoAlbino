/* Nessuna libreria esterna: dati, grafici e CSV restano nel sito. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const fields = {
    temperatura_c: {label:'Temperatura', unit:'°C', id:'temperature', min:-80, max:65},
    umidita_pct: {label:'Umidità', unit:'%', id:'humidity', min:0, max:100},
    pressione_hpa: {label:'Pressione', unit:'hPa', id:'pressure', min:800, max:1100},
    vento_kmh: {label:'Vento', unit:'km/h', id:'wind', min:0, max:400}
  };
  const fmt = new Intl.NumberFormat('it-IT', {maximumFractionDigits:1});
  const dateFmt = new Intl.DateTimeFormat('it-IT', {timeZone:'Europe/Rome', day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
  const tickFmt = new Intl.DateTimeFormat('it-IT', {timeZone:'Europe/Rome',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
  let history = [], period = '24', metric = 'temperatura_c', latest = null, latestFailed = false;
  let discarded = 0;
  function numeric(value, key) {
    if (value === null || value === undefined || typeof value === 'boolean' || String(value).trim() === '') return null;
    const n = Number(value), f = fields[key];
    return Number.isFinite(n) && n >= f.min && n <= f.max ? n : null;
  }
  function timestamp(raw) {
    if (typeof raw !== 'string') return NaN;
    let normalized = raw.trim();
    // Il vecchio workflow Ubuntu salvava date prive di fuso (assunte UTC).
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(normalized)) normalized = normalized.replace(' ', 'T') + 'Z';
    if (!/(Z|[+-]\d{2}:\d{2})$/.test(normalized)) return NaN;
    return Date.parse(normalized);
  }
  function normalize(record) {
    if (!record || typeof record !== 'object') return null;
    const time = timestamp(record.observed_at || record.timestamp);
    if (!Number.isFinite(time) || time > Date.now() + 300000) return null;
    const result = {...record, time};
    Object.keys(fields).forEach(key => result[key] = numeric(record[key], key));
    return Object.keys(fields).some(key => result[key] !== null) ? result : null;
  }
  function display(value) { return value === null ? '—' : fmt.format(value); }
  async function getFile(path) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path + '?t=' + Date.now(), {cache:'no-store',signal:controller.signal});
      if (!response.ok) throw new Error('Dati non disponibili');
      return await response.text();
    } finally { clearTimeout(timeout); }
  }
  function showStatus() {
    if (!latest) {
      $('status').textContent = 'Dati non disponibili'; $('status').className = 'status error';
      $('updated').textContent = 'Non è stato possibile leggere l’ultima osservazione.';
      $('notice').hidden = false;
      $('notice').textContent = location.protocol === 'file:' ? 'Per leggere i dati apri il sito con il collegamento di anteprima, oppure pubblicalo su GitHub Pages.' : 'Riprova più tardi. Se disponibile, puoi comunque consultare l’archivio qui sotto.';
      return;
    }
    const age = (Date.now() - latest.time) / 60000;
    const stale = age > 90;
    const knownTime = Boolean(latest.observed_at);
    const incomplete = Object.keys(fields).some(key => latest[key] === null);
    $('status').textContent = latestFailed ? 'Verifica non riuscita' : stale ? 'Aggiornamento in ritardo' : incomplete ? 'Dati parziali' : knownTime ? 'Misura recente' : 'Acquisizione recente';
    $('status').className = 'status' + ((stale || latestFailed || incomplete) ? ' warning' : '');
    $('updated').textContent = (knownTime ? 'Ora della misura: ' : 'Ultima acquisizione: ') + dateFmt.format(latest.time);
    const messages = [];
    if (latestFailed) messages.push('Non è stato possibile verificare nuovi dati. Restano visibili gli ultimi letti.');
    if (stale) messages.push('Questo campione risale a oltre 90 minuti fa: non descrive necessariamente le condizioni attuali.');
    if (incomplete) messages.push('Alcuni valori sono mancanti o non validi e sono mostrati con un trattino.');
    if (!knownTime) messages.push('L’ora del sensore non è disponibile: la data indica l’acquisizione, non una conferma della freschezza della misura.');
    $('notice').hidden = messages.length === 0;
    $('notice').textContent = messages.join(' ');
  }
  function selectedRows() {
    if (!history.length) return [];
    const end = history[history.length-1].time;
    return history.filter(row => period === 'all' || row.time >= end - Number(period)*3600000);
  }
  function svgElement(name, attrs, text) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attrs || {}).forEach(([key,value]) => el.setAttribute(key, String(value)));
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function render() {
    const rows = selectedRows(), valid = rows.filter(row => row[metric] !== null), f = fields[metric];
    $('download').disabled = !rows.length;
    $('count').textContent = valid.length + ' / ' + rows.length;
    const values = valid.map(row => row[metric]);
    const low = values.length ? Math.min(...values) : null, high = values.length ? Math.max(...values) : null;
    $('min').textContent = display(low) + (low === null ? '' : ' ' + f.unit);
    $('max').textContent = display(high) + (high === null ? '' : ' ' + f.unit);
    $('period-label').textContent = rows.length ? dateFmt.format(rows[0].time) + ' → ' + dateFmt.format(rows[rows.length-1].time) + (discarded ? ' · ' + discarded + ' righe non leggibili escluse' : '') : 'Nessuna osservazione disponibile nel periodo.';
    const chart = $('chart'); chart.replaceChildren();
    chart.setAttribute('aria-label', f.label + ': ' + valid.length + ' campioni validi. Minima ' + display(low) + ', massima ' + display(high) + ' ' + f.unit + '. Dati consultabili nella tabella sottostante.');
    if (!valid.length) chart.textContent = 'Nessun campione valido per questa variabile.';
    else {
      const width=Math.max(280,Math.min(chart.clientWidth || 960,960)), height=260, left=48, right=12, top=25, bottom=42;
      const svg=svgElement('svg',{viewBox:`0 0 ${width} ${height}`,'aria-hidden':'true'});
      const span=Math.max(high-low, 1), yMin=Math.max(f.min,low-span*.16), yMax=Math.min(f.max,high+span*.2);
      let xMin=rows[0].time, xMax=rows[rows.length-1].time;
      if(xMin===xMax){xMin-=1800000;xMax+=1800000;}
      const x=time=>left+(time-xMin)/(xMax-xMin)*(width-left-right);
      const y=value=>top+(yMax-value)/(yMax-yMin)*(height-top-bottom);
      for(let i=0;i<5;i++){
        const value=yMin+(yMax-yMin)*i/4, pos=y(value);
        svg.append(svgElement('line',{x1:left,y1:pos,x2:width-right,y2:pos,stroke:'#e7ece4','stroke-dasharray':'3 5'}));
        svg.append(svgElement('text',{x:left-12,y:pos+4,'text-anchor':'end',fill:'#64756b','font-size':12},fmt.format(value)));
      }
      svg.append(svgElement('text',{x:left,y:13,fill:'#64756b','font-size':12},f.unit));
      const ticks=width<500?2:4;
      for(let i=0;i<ticks;i++){
        const t=xMin+(xMax-xMin)*i/(ticks-1);
        svg.append(svgElement('text',{x:x(t),y:height-13,'text-anchor':i===0?'start':i===ticks-1?'end':'middle',fill:'#64756b','font-size':12},tickFmt.format(t)));
      }
      let segment=[];
      const flush=()=>{
        if(!segment.length)return;
        const d=segment.map((r,i)=>(i?'L':'M')+x(r.time).toFixed(2)+','+y(r[metric]).toFixed(2)).join(' ');
        if(segment.length>1){
          svg.append(svgElement('path',{d:d+` L${x(segment[segment.length-1].time)},${height-bottom} L${x(segment[0].time)},${height-bottom} Z`,fill:'#edf3e8'}));
          svg.append(svgElement('path',{d,fill:'none',stroke:'#39725a','stroke-width':2.4,'stroke-linejoin':'round','stroke-linecap':'round'}));
        }
        segment.forEach(r=>{
          const dot=svgElement('circle',{cx:x(r.time),cy:y(r[metric]),r:segment.length===1?3:2,fill:'#39725a'});
          dot.append(svgElement('title',{},dateFmt.format(r.time)+' · '+fmt.format(r[metric])+' '+f.unit));svg.append(dot);
        });
        segment=[];
      };
      rows.forEach(row=>{
        if(row[metric]===null){flush();return;}
        if(segment.length && row.time-segment[segment.length-1].time>90*60000)flush();
        segment.push(row);
      });flush();chart.append(svg);
    }
    const fragment=document.createDocumentFragment();
    rows.forEach(row=>{
      const tr=document.createElement('tr');
      [dateFmt.format(row.time),...Object.keys(fields).map(key=>display(row[key]))].forEach(text=>{const td=document.createElement('td');td.textContent=text;tr.append(td);});fragment.append(tr);
    });$('data-rows').replaceChildren(fragment);
  }
  async function loadLatest(){
    try {
      const row=normalize(JSON.parse(await getFile('ultimo_stato.json')));
      if(!row)throw new Error('Osservazione non valida');
      latest=row;latestFailed=false;
      Object.entries(fields).forEach(([key,f])=>$ (f.id).textContent=display(row[key]));
    }catch{latestFailed=true;}showStatus();
  }
  async function loadHistory(){
    try{
      const text=await getFile('storico_albanello.jsonl');
      const unique=new Map();let bad=0;
      text.split(/\r?\n/).forEach(line=>{if(!line.trim())return;try{const row=normalize(JSON.parse(line));if(row)unique.set(row.time,row);else bad++;}catch{bad++;}});
      if(!unique.size)throw new Error('Archivio vuoto');
      history=[...unique.values()].sort((a,b)=>a.time-b.time);discarded=bad;render();
    }catch{
      if(!history.length)render();
      $('period-label').textContent=history.length?'Archivio non aggiornabile: restano visibili i campioni già caricati.':'Archivio non disponibile. I dati attuali, se leggibili, restano visibili sopra.';
    }
  }
  document.querySelectorAll('[data-period]').forEach(button=>button.addEventListener('click',()=>{
    period=button.dataset.period;document.querySelectorAll('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render();
  }));
  document.querySelectorAll('[data-metric]').forEach(button=>button.addEventListener('click',()=>{
    metric=button.dataset.metric;document.querySelectorAll('[data-metric]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render();
  }));
  $('download').addEventListener('click',()=>{
    const rows=selectedRows();
    const lines=['data_utc;temperatura_c;umidita_pct;pressione_hpa;vento_kmh',...rows.map(row=>[new Date(row.time).toISOString(),...Object.keys(fields).map(key=>row[key]===null?'':String(row[key]).replace('.',','))].join(';'))];
    const url=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='meteoalbino-'+period+'.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  Promise.allSettled([loadLatest(),loadHistory()]);
  setInterval(()=>Promise.allSettled([loadLatest(),loadHistory()]),300000);
  setInterval(showStatus,60000);
  let resizeTimer;
  window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,150);});
})();
