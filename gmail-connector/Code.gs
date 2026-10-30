/** Private pilot connector. Configure Script Properties; never put secrets in source. */
function syncCaseTriage() {
  const guard=LockService.getScriptLock();
  if (!guard.tryLock(1000)) return;
  try {
    const props=PropertiesService.getScriptProperties();
    const url=props.getProperty('INTAKE_URL');
    const secret=props.getProperty('EMAIL_WEBHOOK_SECRET');
    if(!url || !/^https:\/\/[^/]+\/integrations\/gmail$/.test(url) || !secret || secret.length<32)
      throw new Error('Set HTTPS INTAKE_URL and EMAIL_WEBHOOK_SECRET in Script Properties.');
    const mailbox=Gmail.Users.getProfile('me').emailAddress;
    const labels=Gmail.Users.Labels.list('me').labels || [];
    const label=labels.find(l=>l.name==='CaseTriage');
    if(!label)throw new Error('Create the CaseTriage label in your test Gmail inbox first.');
    const options={labelIds:[label.id],q:'newer_than:30d -in:sent -in:drafts -in:spam -in:trash',maxResults:20};
    const cursor=props.getProperty('PAGE_CURSOR');if(cursor)options.pageToken=cursor;
    let page;
    try {page=Gmail.Users.Messages.list('me',options);}
    catch(error){props.deleteProperty('PAGE_CURSOR');throw new Error('Gmail listing failed. Cursor reset; retry sync.');}
    let sent=JSON.parse(props.getProperty('ACK_IDS') || '[]');let accepted=0,failed=0;
    for(const info of page.messages || []) {
      if(sent.includes(info.id))continue;
      const message=Gmail.Users.Messages.get('me',info.id,{format:'raw'});
      if(!message.raw || message.raw.length>340000){failed++;continue;}
      const response=UrlFetchApp.fetch(url,{
        method:'post',contentType:'application/json',headers:{Authorization:'Bearer '+secret},
        payload:JSON.stringify({mailbox:mailbox,message_id:message.id,thread_id:message.threadId,raw:message.raw}),
        muteHttpExceptions:true,followRedirects:false
      });
      const code=response.getResponseCode();
      let acknowledged=false;
      if(code===200){try {acknowledged=['draft_saved','duplicate'].includes(JSON.parse(response.getContentText()).status);} catch(error){}}
      if(acknowledged){sent.push(info.id);sent=sent.slice(-250);props.setProperty('ACK_IDS',JSON.stringify(sent));accepted++;}
      else if(code===401 || code===403 || code===503)throw new Error('Intake authorization/configuration unavailable. Check private service configuration.');
      else failed++;
    }
    if(page.nextPageToken)props.setProperty('PAGE_CURSOR',page.nextPageToken);else props.deleteProperty('PAGE_CURSOR');
    console.log('Case Triage sync: '+accepted+' accepted; '+failed+' skipped or failed. No message contents logged.');
  } finally {guard.releaseLock();}
}
