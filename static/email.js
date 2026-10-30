async function loadEmailDrafts() {
    try {
        const drafts=await api('/email-drafts');const list=$('#email-drafts');list.replaceChildren();
        if(!drafts.length)list.append(el('p','No email drafts yet. Label a fictional email CaseTriage in the connected test inbox.'));
        drafts.forEach(d=>{
            const item=el('article',undefined,'clarification-entry');
            item.append(el('h3',d.messages[0].subject),el('p',`${d.messages[0].sender} · ${d.messages.length} message(s) · ${d.received_at}`));
            const source=el('details');source.append(el('summary','Original email text'));
            d.messages.forEach(m=>source.append(el('h4',`${m.subject} — ${m.sender}`),el('p',m.body,'description')));item.append(source);
            const button=el('button',d.linked_case_id ? 'Open linked case' : 'Review draft','secondary');button.type='button';
            button.onclick=()=>d.linked_case_id ? openCase(d.linked_case_id) : reviewEmailDraft(d);
            item.append(button);
            if(d.has_new_messages)item.append(el('p','New messages arrived after case creation. Review the original email text here; they are not automatically applied to saved case ratings.','muted'));
            list.append(item);
        });
    } catch(error){notice(error.message,true);}
}
api('/demo-config').then(config=>{
    if(config.email_intake){$('#email-panel').hidden=false;$('#refresh-emails').onclick=loadEmailDrafts;loadEmailDrafts();}
}).catch(()=>{});
