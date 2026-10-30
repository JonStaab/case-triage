let workflowActor = '';
function renderWorkflow(panel,c) {
 const w=c.workflow || {owner:'',actions:[],events:[]};const section=el('section');
 section.append(el('h3','Ownership and follow-through'),el('p','Case owner: '+(w.owner||'Unassigned')),
 el('p','Activity times are reported by the person entering them. Recording times come from the server. Names are not verified identities in this demo.','muted'));
 const signalBox=el('div');
 const attention=c.attention;
 if(attention){
  signalBox.append(el('h4','Needs attention'));
  attention.signals.forEach(message=>signalBox.append(el('p',message)));
  if(!attention.signals.length)signalBox.append(el('p',attention.active?'No current attention flags.':'Closed case — attention flags paused.','muted'));
  if(!attention.acknowledgment_recorded && attention.elapsed_since_creation_seconds!==null && attention.active){
   const timer=el('p',undefined,'muted');const starting=Date.now();
   const tick=()=>{const seconds=attention.elapsed_since_creation_seconds+Math.floor((Date.now()-starting)/1000);timer.textContent=`Since case creation: ${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m — acknowledgment not recorded.`;};tick();
   const interval=setInterval(()=>{if(!timer.isConnected){clearInterval(interval);return;}tick();},30000);signalBox.append(timer);
  }
  signalBox.append(el('p','These are recorded-workflow signals, not proof that someone failed to act. No company response SLA is configured.','muted'));
 }section.append(signalBox);
 const date=value=>value ? new Date(value).toLocaleString() : 'Unknown';
 async function submit(path,data) {
  try {await api(`/cases/${encodeURIComponent(c.unique_id)}${path}`,jsonOptions(path==='/owner'?'PATCH':'POST',{expected_revision:c.revision,...data}));await loadCases();await openCase(c.unique_id);notice('Case activity saved.');}
  catch(error){notice(error.message,true);}
 }
 function input(form,title,name,type='text',required=true){const label=el('label',title),field=el(type==='textarea'?'textarea':'input');if(type!=='textarea')field.type=type;field.name=name;field.required=required;field.maxLength=type==='textarea'?2000:100;label.append(field);form.append(label);return field;}
 function editor(title){const details=el('details'),form=el('form');details.append(el('summary',title),form);section.append(details);const actor=input(form,'Recorded by (remembered on this page only)','actor');actor.value=workflowActor;actor.oninput=()=>{workflowActor=actor.value;};return form;}
 function saveButton(form,title){const b=el('button',title);b.type='submit';form.append(b);}
 if(!c.deleted_at && c.status!=='Resolved') {
  const form=editor('Assign case owner');input(form,'Responsible case owner','owner').value=w.owner;saveButton(form,'Save owner');form.onsubmit=e=>{e.preventDefault();submit('/owner',Object.fromEntries(new FormData(form)));};
  const af=editor('Assign a next action');input(af,'Action needed','description','textarea');const responsible=input(af,'Responsible person','responsible');responsible.value=w.owner||workflowActor;
  af.elements.actor.addEventListener('change',()=>{if(!responsible.value)responsible.value=af.elements.actor.value;});
  input(af,'Waiting on (optional)','waiting_on','text',false);
  const kindLabel=el('label','Timing / commitment type'),kind=el('select');kind.name='kind';
  [['immediate','ASAP — no invented deadline'],['follow_up','Follow-up checkpoint'],['client_update','Promised client update'],['vendor_response','Promised vendor response'],['commitment','Other dated commitment']].forEach(([value,text])=>{const option=el('option',text);option.value=value;kind.append(option);});kindLabel.append(kind);af.append(kindLabel);
  const due=input(af,'Checkpoint / commitment date and time (optional for ASAP; local time)','due_at','datetime-local',false);
  const explanation=el('p','ASAP means act promptly. The app tracks elapsed time; it does not invent an overdue deadline.','muted');af.append(explanation);
  kind.onchange=()=>{due.required=kind.value!=='immediate';explanation.textContent=kind.value==='immediate'?'No date required. If waiting on someone, add a follow-up checkpoint when appropriate.':'Record an agreed time or a checkpoint you deliberately set. This is not a case resolution deadline.';};
  saveButton(af,'Save action');af.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(af));data.due_at=data.due_at?new Date(data.due_at).toISOString():null;submit('/actions',data);};
 }
 w.actions.forEach(a=>{
  const row=el('div',undefined,'clarification-entry');row.append(el('h4',a.description),el('p',`Responsible: ${a.responsible} · Waiting on: ${a.waiting_on||'Not specified'} · ${a.kind==='immediate' ? 'ASAP' : a.kind ? a.kind.replaceAll('_',' ') : 'Existing dated action'} · ${a.due_at ? 'Checkpoint / commitment: '+date(a.due_at) : 'ASAP — no dated commitment'}`),el('p',a.completed_at?`Completed: ${date(a.completed_at)} — ${a.outcome}`:a.due_at && new Date(a.due_at)<new Date()?'Checkpoint / commitment overdue — action remains open':'Open action'));
  if(!a.completed_at && !c.deleted_at && c.status!=='Resolved'){
   const form=el('form');const actor=input(form,'Completed by (reported name)','actor');actor.value=workflowActor;actor.oninput=()=>{workflowActor=actor.value;};input(form,'Outcome / what was done','outcome','textarea');saveButton(form,'Record completion');form.onsubmit=e=>{e.preventDefault();submit(`/actions/${encodeURIComponent(a.id)}/complete`,Object.fromEntries(new FormData(form)));};row.append(form);
  }section.append(row);
 });
 if(!c.deleted_at){const form=editor('Record PM activity or client update');const label=el('label','Activity type'),select=el('select');select.name='kind';[['initial_response','First human acknowledgment'],['information_requested','Requested information'],['follow_up','Pursued / followed up'],['information_received','Information received'],['client_updated','Updated the client'],['resolution_note','Resolution evidence / note'],['note','General note / correction']].forEach(([v,t])=>{const o=el('option',t);o.value=v;select.append(o);});label.append(select);form.append(label);input(form,'What happened? Include a source/reference if available.','details','textarea');input(form,'When it happened (optional; local time)','occurred_at','datetime-local',false);saveButton(form,'Save activity');form.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));data.occurred_at=data.occurred_at?new Date(data.occurred_at).toISOString():null;submit('/activities',data);};}
 function eventDetails(event){
  const d=event.details;if(typeof d==='string')return d;
  if(d.description)return `${d.description} — responsible: ${d.responsible}; waiting on: ${d.waiting_on||'not specified'}; checkpoint/commitment: ${d.due_at?date(d.due_at):'none (ASAP)'}`+(d.outcome?`; outcome: ${d.outcome}`:'');
  if(event.kind==='owner_assigned')return `Owner changed from ${d.previous||'unassigned'} to ${d.owner}.`;
  if(event.kind==='case_status_changed')return `Status: ${d.previous} → ${d.status}. ${d.in_trash?'Moved to Trash.':''}`;
  if(event.kind==='assessment_or_context_saved')return `Assessment/context saved. Impact: ${d.previous_impact} → ${d.impact}; urgency: ${d.previous_urgency} → ${d.urgency}.`;
  return 'Case record updated.';
 }
 section.append(el('h3','Case timeline'));
 if(!w.events.length)section.append(el('p','No recorded history. Earlier actions are unknown; timestamps have not been invented.','muted'));
 const titles={case_created:'Case created',owner_assigned:'Owner assigned',case_status_changed:'Status changed',action_assigned:'Action assigned',action_completed:'Action completed',assessment_or_context_saved:'Assessment updated',initial_response:'First acknowledgment',information_requested:'Information requested',follow_up:'Followed up',information_received:'Information received',client_updated:'Client updated',resolution_note:'Resolution note',note:'Note'};
 [...w.events].reverse().forEach(event=>{
  const row=el('div',undefined,'clarification-entry');
  row.append(el('strong',titles[event.kind]||event.kind.replaceAll('_',' ')),el('p',`${date(event.occurred_at)} · ${event.actor||'System'}`,'muted'),el('p',eventDetails(event),'description'));
  // Preserve both audit timestamps, but only display a second time for a later entry.
  if(event.recorded_at && Math.abs(new Date(event.recorded_at)-new Date(event.occurred_at))>=60000)row.append(el('p',`Logged later: ${date(event.recorded_at)}`,'muted'));
  section.append(row);
 });panel.append(section);
}
