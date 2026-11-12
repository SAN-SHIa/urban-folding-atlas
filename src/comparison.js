// Distances are API route lengths, not straight-line or simplified geometry lengths.
function renderComparison({routes, scope, enabled, names, colors, sameNode}) {
  const root=document.getElementById('comparisonCharts');
  root.replaceChildren();
  const median=values=>{if(!values.length)return null;values.sort((a,b)=>a-b);const mid=Math.floor(values.length/2);return values.length%2?values[mid]:(values[mid-1]+values[mid])/2};
  const stats=Object.keys(names).map(mode=>{
    const selected=routes.filter(r=>r.mode===mode);
    const distances=selected.map(r=>r.distance).filter(v=>v!==''&&v!==null&&v!==undefined).map(Number).filter(v=>Number.isFinite(v)&&v>0);
    const durations=selected.map(r=>r.duration).filter(v=>Number.isFinite(v)&&v>0);
    return {mode,distance:median(distances.map(v=>v/1000)),time:median(durations.map(v=>v/60)),distanceCount:distances.length,timeCount:durations.length};
  });
  document.getElementById('comparisonContext').textContent=scope==='pair'?'Selected directed pair · filtered modes and durations':'Median across current filtered routes · available samples per mode, not matched pairs';
  const records=[];
  for(const metric of [{key:'distance',title:'Path length',unit:'km',count:'distanceCount'},{key:'time',title:'Commute time',unit:'min',count:'timeCount'}]){
    const panel=document.createElement('div');panel.className='comparison-panel';
    const heading=document.createElement('h3');heading.textContent=metric.title;panel.append(heading);
    const max=Math.max(0,...stats.map(s=>s[metric.key]??0));
    // Each chart has its own shared zero-based scale across all four modes.
    const ceiling=max>0?Math.ceil(max/Math.pow(10,Math.floor(Math.log10(max))))*Math.pow(10,Math.floor(Math.log10(max))):1;
    const axis=document.createElement('div');axis.className='chart-axis';axis.innerHTML=`<span>0</span><span>${Number((ceiling/2).toPrecision(3))}</span><span>${ceiling} ${metric.unit}</span>`;panel.append(axis);
    for(const stat of stats){
      const value=stat[metric.key],row=document.createElement('div');row.className='chart-row';
      const title=document.createElement('div');title.className='chart-row-title';
      const label=document.createElement('span');label.textContent=names[stat.mode];
      const output=document.createElement('strong');output.textContent=value===null?'—':`${value.toFixed(metric.key==='distance'?2:1)} ${metric.unit}`;title.append(label,output);
      const track=document.createElement('div');track.className='chart-track';track.setAttribute('role','img');
      track.setAttribute('aria-label',`${names[stat.mode]} ${metric.title}: ${output.textContent}`);
      if(value!==null){const bar=document.createElement('div');bar.className='chart-bar';bar.style.width=`${value/ceiling*100}%`;bar.style.background=colors[stat.mode];track.append(bar)}
      const note=document.createElement('span');note.className='chart-sample';note.textContent=!enabled.has(stat.mode)?'Layer disabled':sameNode&&scope==='pair'?'Same node · not queried':value===null?'No valid data under current filters':`n = ${stat[metric.count].toLocaleString()}${scope==='pair'?' route':' routes · median'}`;
      row.append(title,track,note);panel.append(row);
      records.push({mode:stat.mode,metric:metric.key,value,n:stat[metric.count]});
    }
    root.append(panel);
  }
  window.atlasComparison=records;
}
