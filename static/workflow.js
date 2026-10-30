function renderWorkflow(panel,c) {
 const w=c.workflow || {owner:'',actions:[],events:[]};const section=el('section');
 section.append(el('h3','Ownership and follow-through'),el('p','Case owner: '+(w.owner||'Unassigned')),
 el('p','Activity times are reported by the person entering them. Recording times come from the server. Names are not verified identities in this demo.','muted'));
 const date=value=>value ? new Date(value).toLocaleString() : 'Unknown';
 async function submit(path,data) {
  try {await api(`/cases/${encodeURIComponent(c.unique_id)}${path}`,jsonOptions(path==='/owner'?'PATCH':'POST',{expected_revision:c.revision,...data}));await loadCases();await openCase(c.unique_id);notice('Case activity saved.');}
  catch(error){notice(error.message,true);}
 }
 function input(form,title,name,type='text',required=true){const label=el('label',title),field=el(type==='textarea'?'textarea':'input');if(type!=='textarea')field.type=type;field.name=name;field.required=required;field.maxLength=type==='textarea'?2000:100;label.append(field);form.append(label);return field;}
 function editor(title){const details=el('details'),form=el('form');details.append(el('summary',title),form);section.append(details);input(form,'Recorded by (your name)','actor');return form;}
 function saveButton(form,title){const b=el('button',title);b.type='submit';form.append(b);}
 if(!c.deleted_at && c.status!=='Resolved') {
  const form=editor('Assign case owner');input(form,'Responsible case owner','owner').value=w.owner;saveButton(form,'Save owner');form.onsubmit=e=>{e.preventDefault();submit('/owner',Object.fromEntries(new FormData(form)));};
  const af=editor('Assign a next action');input(af,'Action needed','description','textarea');input(af,'Responsible person','responsible');input(af,'Waiting on (optional)','waiting_on','text',false);input(af,'Due date and time (your local time)','due_at','datetime-local');saveButton(af,'Save action');af.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(af));data.due_at=new Date(data.due_at).toISOString();submit('/actions',data);};
 }
 w.actions.forEach(a=>{
  const row=el('div',undefined,'clarification-entry');row.append(el('h4',a.description),el('p',`Responsible: ${a.responsible} · Waiting on: ${a.waiting_on||'Not specified'} · Due: ${date(a.due_at)}`),el('p',a.completed_at?`Completed: ${date(a.completed_at)} — ${a.outcome}`:new Date(a.due_at)<new Date()?'Overdue — action remains open':'Open action'));
  if(!a.completed_at && !c.deleted_at && c.status!=='Resolved'){
   const form=el('form');input(form,'Completed by (reported name)','actor');input(form,'Outcome / what was done','outcome','textarea');saveButton(form,'Record completion');form.onsubmit=e=>{e.preventDefault();submit(`/actions/${encodeURIComponent(a.id)}/complete`,Object.fromEntries(new FormData(form)));};row.append(form);
  }section.append(row);
 });
 if(!c.deleted_at){const form=editor('Record PM activity or client update');const label=el('label','Activity type'),select=el('select');select.name='kind';[['initial_response','First human acknowledgment'],['information_requested','Requested information'],['follow_up','Pursued / followed up'],['information_received','Information received'],['client_updated','Updated the client'],['resolution_note','Resolution evidence / note'],['note','General note / correction']].forEach(([v,t])=>{const o=el('option',t);o.value=v;select.append(o);});label.append(select);form.append(label);input(form,'What happened? Include a source/reference if available.','details','textarea');input(form,'When it happened (optional; local time)','occurred_at','datetime-local',false);saveButton(form,'Save activity');form.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));data.occurred_at=data.occurred_at?new Date(data.occurred_at).toISOString():null;submit('/activities',data);};}
 section.append(el('h3','Case timeline'));
 if(!w.events.length)section.append(el('p','No recorded history. Earlier actions are unknown; timestamps have not been invented.','muted'));
 [...w.events].reverse().forEach(event=>{const row=el('div',undefined,'clarification-entry');row.append(el('strong',event.kind.replaceAll('_',' ')),el('p',`Occurred: ${date(event.occurred_at)} · Recorded: ${date(event.recorded_at)} · ${event.actor} (${event.source})`),el('p',typeof event.details==='string'?event.details:JSON.stringify(event.details),'description'));section.append(row);});panel.append(section);
}
