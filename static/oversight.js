/* Views over the same records, not authentication or verified employee scoring. */
function oversightMetrics(cases, now=Date.now()) {
 const saved=cases.filter(c=>!c.deleted_at), active=saved.filter(c=>c.status!=='Resolved');
 const actions=c=>(c.workflow?.actions||[]);
 const open=c=>actions(c).filter(a=>!a.completed_at);
 const overdue=a=>a.due_at && Number.isFinite(Date.parse(a.due_at)) && Date.parse(a.due_at)<now;
 const validResponses=saved.map(c=>c.attention?.first_recorded_response_seconds).filter(v=>typeof v==='number' && Number.isFinite(v) && v>=0).sort((a,b)=>a-b);
 const median=validResponses.length ? (validResponses[Math.floor((validResponses.length-1)/2)]+validResponses[Math.floor(validResponses.length/2)])/2 : null;
 function commitments(kind){
  const due=saved.flatMap(actions).filter(a=>a.kind===kind && a.due_at && Number.isFinite(Date.parse(a.due_at)) && Date.parse(a.due_at)<=now);
  return {due:due.length,onTime:due.filter(a=>a.completed_at && Date.parse(a.completed_at)<=Date.parse(a.due_at)).length};
 }
 const unassigned=active.filter(c=>!c.workflow?.owner?.trim());
 const noAction=active.filter(c=>!open(c).length);
 const late=active.filter(c=>open(c).some(overdue));
 const waiting=active.filter(c=>open(c).some(a=>a.waiting_on && !a.due_at) && !open(c).some(a=>a.kind==='follow_up' && a.due_at));
 const noAck=active.filter(c=>!c.attention?.acknowledgment_recorded);
 const exceptions=active.map(c=>({c,reasons:[...(unassigned.includes(c)?['No case owner']:[]),...(noAction.includes(c)?['No open next action']:[]),...(late.includes(c)?['Overdue checkpoint / commitment']:[]),...(waiting.includes(c)?['Waiting without a follow-up checkpoint']:[]),...(noAck.includes(c)?[c.created_at?'Acknowledgment not recorded':'Earlier acknowledgment history unknown']:[])]})).filter(x=>x.reasons.length).sort((a,b)=>a.c.priority.localeCompare(b.c.priority));
 const owners=[...new Set(active.map(c=>c.workflow?.owner?.trim()||'Unassigned'))].sort();
 return {active:active.length,unassigned:unassigned.length,noAction:noAction.length,late:late.length,waiting:waiting.length,noAck:noAck.length,median,responseSamples:validResponses.length,followups:commitments('follow_up'),updates:commitments('client_update'),exceptions,
  owners:owners.map(owner=>{const own=active.filter(c=>(c.workflow?.owner?.trim()||'Unassigned')===owner);return {owner,cases:own.length,p1:own.filter(c=>c.priority==='P1').length,late:own.filter(c=>late.includes(c)).length,noAction:own.filter(c=>noAction.includes(c)).length};})};
}
let workspaceMode='team', workspacePerson='', oversightCases=[];
function matchesPerson(c,name){const key=name.trim().toLocaleLowerCase();return !!key && ((c.workflow?.owner||'').trim().toLocaleLowerCase()===key || (c.workflow?.actions||[]).some(a=>!a.completed_at && (a.responsible||'').trim().toLocaleLowerCase()===key));}
function renderOversight(cases){
 oversightCases=cases;
 const roster=$('#pm-names');roster.replaceChildren();
 [...new Set(cases.flatMap(c=>[c.workflow?.owner,...(c.workflow?.actions||[]).map(a=>a.responsible)]).filter(Boolean))].sort().forEach(name=>{const o=el('option');o.value=name;roster.append(o);});
 const panel=$('#director-dashboard');panel.hidden=workspaceMode!=='director';
 $('#pm-person-label').hidden=workspaceMode!=='pm';
 $('#workspace-help').textContent=workspaceMode==='pm'?'Enter your recorded name to see cases you own or have an open action on. This is a convenience filter, not a signed-in identity.':workspaceMode==='director'?'Review exceptions and recorded follow-through across the team. Open any case to inspect its evidence and timeline.':'All team cases, in priority order.';
 if(workspaceMode!=='director')return;
 const m=oversightMetrics(cases);panel.replaceChildren(el('h2','Director overview'),el('p','Scope: all retained cases except Trash. Workload and exceptions use active cases. Figures refresh with the queue.','muted'));
 const cards=el('div',undefined,'metric-grid');
 [['Active cases',m.active],['Unassigned',m.unassigned],['No open next action',m.noAction],['Overdue commitments',m.late],['Waiting without checkpoint',m.waiting],['Acknowledgment unrecorded / unknown',m.noAck]].forEach(([title,value])=>{const card=el('div',undefined,'metric');card.append(el('strong',String(value)),el('span',title));cards.append(card);});panel.append(cards);
 const rate=v=>v.due?`${Math.round(100*v.onTime/v.due)}% (${v.onTime}/${v.due})`:'No commitments due yet';
 panel.append(el('h3','Recorded follow-through'),el('p',`Follow-up checkpoints met: ${rate(m.followups)}`),el('p',`Client update commitments met: ${rate(m.updates)}`),el('p',`Median first acknowledgment: ${m.median===null?'Not enough recorded data':Math.round(m.median/60)+' minutes'} · ${m.responseSamples} measured cases`),el('p','Commitment rates count dated commitments due by now, including resolved cases; completion must be recorded on or before the due time. ASAP actions are excluded. First acknowledgment measures case creation to the first explicitly logged human acknowledgment; unknown or invalid times are excluded.','muted'));
 panel.append(el('p','These are self-reported workflow records, not verified employee performance. Current ownership is not necessarily the owner when an activity occurred. No response SLA or employee ranking is applied.','muted'));
 const table=el('table'),head=el('tr');['Current owner','Active cases','P1','With overdue commitments','Without next action'].forEach(t=>{const th=el('th',t);th.scope='col';head.append(th);});const thead=el('thead');thead.append(head);table.append(thead);const tbody=el('tbody');
 m.owners.forEach(o=>{const row=el('tr');[o.owner,o.cases,o.p1,o.late,o.noAction].forEach(v=>row.append(el('td',String(v))));tbody.append(row);});table.append(tbody);const wrap=el('div',undefined,'table-scroll');wrap.append(table);panel.append(el('h3','Current workload by owner'),wrap,el('h3','Cases to review'));
 if(!m.exceptions.length)panel.append(el('p','No current exceptions.'));
 m.exceptions.forEach(({c,reasons})=>{const b=el('button',undefined,'case-row');b.type='button';b.append(el('strong',c.customer_name+' · '+c.priority),el('small',reasons.join(' · ')));b.onclick=async()=>{await openCase(c.unique_id);$('#detail').scrollIntoView({behavior:'smooth',block:'start'});};panel.append(b);});
}
if(typeof module!=='undefined')module.exports={oversightMetrics,matchesPerson};
