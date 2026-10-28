const $ = selector => document.querySelector(selector);
let selectedId = null;
let queueView = 'active';
let intakeVersion = 0;
let intakeClarifications = [];
const labels = {P1: 'Critical', P2: 'High', P3: 'Medium', P4: 'Low'};
const impacts = ['Low', 'Medium', 'High', 'Critical'];
const urgencies = ['Low', 'Medium', 'High', 'Urgent', 'Critical'];

function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
}
function notice(text, error = false) {
    const node = $('#message');
    node.textContent = text;
    node.className = error ? 'error' : '';
    node.hidden = false;
}
async function api(path, options = {}) {
    let response;
    try { response = await fetch(path, options); }
    catch { throw new Error('Cannot reach the server. Check your connection and try again.'); }
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The server returned an unexpected response. Please try again.'); }
    if (!response.ok) {
        const detail = data.detail;
        throw new Error(Array.isArray(detail)
            ? detail.map(item => `${item.loc.at(-1)}: ${item.msg}`).join('; ')
            : detail || 'Request failed. Please try again.');
    }
    return data;
}
function jsonOptions(method, data) {
    return {method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)};
}
function badge(priority) {
    return el('span', `${priority} · ${labels[priority] || ''}`, `badge ${priority}`);
}
function ratingSelect(title, values, value) {
    const label = el('label', title);
    const select = el('select');
    select.setAttribute('aria-label', title);
    const placeholder = el('option', 'Select a rating');
    placeholder.value = '';
    select.append(placeholder);
    values.forEach(value => {
        const option = el('option', value);
        option.value = value;
        select.append(option);
    });
    select.value = value;
    label.append(select);
    return {label, select};
}
function renderClarifications(container, notes, title) {
    container.replaceChildren();
    if (!notes.length) return;
    container.append(el('h4', title));
    notes.forEach(note => {
        const entry = el('div', undefined, 'clarification-entry');
        entry.append(el('strong', note.question), el('p', note.answer, 'description'));
        container.append(entry);
    });
}
function showSuggestion(container, suggestion, context, callbacks) {
    container.replaceChildren();
    container.hidden = false;
    container.dataset.pendingAnswers = '';
    container.append(el('h3', suggestion.assessment_state === 'ready_for_review' ? 'Ready for review' : 'Clarify the assessment'),
        el('p', 'Review the evidence and edit both ratings if needed, then save. Customer tier stays unchanged.', 'muted'));
    for (const [title, value, reason, evidence] of [
        ['Business impact', suggestion.business_impact, suggestion.impact_reason, suggestion.impact_evidence],
        ['Time sensitivity', suggestion.time_sensitivity, suggestion.urgency_reason, suggestion.urgency_evidence]
    ]) {
        container.append(el('h4', `${title}: ${value || 'Needs clarification'}`), el('p', reason));
        evidence.forEach(quote => container.append(el('blockquote', quote)));
    }
    if (suggestion.suggested_priority) {
        container.append(el('p', `Rule-based preview: ${suggestion.suggested_priority} · ${labels[suggestion.suggested_priority]}. Recalculated when you save the reviewed assessment.`, 'muted'));
    }
    const history = el('div');
    renderClarifications(history, context.clarifications, 'Context used in this assessment');
    container.append(history);
    const answerFields = [];
    if (suggestion.missing_information.length) {
        container.append(el('h4', 'Answer follow-up questions'),
            el('p', 'Enter what you know. Leave unknown answers blank. Reassess to use the answers, or save them without changing ratings.', 'muted'));
        suggestion.missing_information.forEach(question => {
            const label = el('label', question);
            const answer = el('textarea');
            answer.rows = 2;
            answer.maxLength = 1500;
            answer.setAttribute('aria-label', question);
            answer.placeholder = 'Your answer (optional)';
            answer.value = context.clarifications.find(note => note.question === question)?.answer || '';
            answerFields.push({question, answer, original: answer.value});
            label.append(answer);
            container.append(label);
        });
    }
    container.append(el('h4', 'Suggested next action'), el('p', suggestion.next_action));
    const impact = ratingSelect('Reviewed business impact', impacts, suggestion.business_impact || '');
    const urgency = ratingSelect('Reviewed time sensitivity', urgencies, suggestion.time_sensitivity || '');
    const fields = el('div', undefined, 'review-fields');
    fields.append(impact.label, urgency.label);
    const confirmed = el('input');
    confirmed.type = 'checkbox';
    const confirmation = el('label', undefined, 'review-confirm');
    confirmation.append(confirmed, el('span', 'I reviewed both ratings, including any choice the AI could not determine.'));
    const apply = el('button', callbacks.applyLabel || 'Save reviewed assessment');
    const help = el('p', '', 'muted');
    apply.type = 'button';
    let busy = false;
    const refreshApply = () => {
        help.textContent = container.dataset.pendingAnswers === 'true' ? 'Reassess changed answers before saving.' : !impact.select.value || !urgency.select.value ? 'Select both ratings or answer the questions and reassess.' : !confirmed.checked ? 'Confirm that you reviewed both ratings to save.' : 'Ready to save the case and its answers.';
        apply.disabled = busy || !confirmed.checked || !impact.select.value || !urgency.select.value || container.dataset.pendingAnswers === 'true';
    };
    confirmed.onchange = refreshApply;
    impact.select.onchange = urgency.select.onchange = () => {
        confirmed.checked = false;
        refreshApply();
    };
    answerFields.forEach(({answer}) => {
        answer.oninput = () => {
            container.dataset.pendingAnswers = String(answerFields.some(field => field.answer.value !== field.original));
            confirmed.checked = false;
            refreshApply();
        };
    });
    function collectAnswers() {
        const merged = new Map(context.clarifications.map(note => [note.question, {...note}]));
        answerFields.forEach(({question, answer, original}) => {
            const value = answer.value.trim();
            if (value) merged.set(question, {question, answer: value});
            else if (original) merged.delete(question);
        });
        if (merged.size > 20) throw new Error('This case has reached the limit of 20 clarification answers.');
        return [...merged.values()];
    }
    const actions = el('div', undefined, 'clarification-actions');
    if (answerFields.length || context.clarifications.length) {
        const reassess = el('button', 'Reassess with answers', 'secondary');
        const save = el('button', callbacks.saveLabel, 'secondary');
        reassess.type = save.type = 'button';
        const run = async work => {
            if (!callbacks.isCurrent()) { notice('The case or form changed. Request a fresh suggestion.', true); return; }
            busy = true;
            reassess.disabled = save.disabled = true;
            refreshApply();
            try { await work(collectAnswers()); }
            catch (error) { notice(error.message, true); }
            finally {
                busy = false;
                reassess.disabled = save.disabled = false;
                refreshApply();
            }
        };
        reassess.onclick = () => run(async notes => {
            if (!notes.length) throw new Error('Enter at least one answer before reassessing.');
            reassess.textContent = 'Reassessing…';
            try {
                const next = {...context, clarifications: notes};
                const result = await api('/triage', jsonOptions('POST', next));
                if (!callbacks.isCurrent()) throw new Error('The case or form changed. Request a fresh suggestion.');
                callbacks.onContext(notes);
                showSuggestion(container, result, next, callbacks);
                notice('Reassessed using your answers. Review the updated suggestions before applying.');
            } finally { reassess.textContent = 'Reassess with answers'; }
        });
        save.onclick = () => run(async notes => {
            if (!notes.length && !context.clarifications.length) throw new Error('Enter at least one answer to save.');
            await callbacks.onSave(notes);
        });
        actions.append(reassess);
        if (callbacks.onSave) actions.append(save);
    }
    container.append(actions, fields);
    if (!suggestion.business_impact || !suggestion.time_sensitivity) {
        container.append(el('p', 'Unanswered ratings are not Low. Provide more context and reassess, or explicitly select both ratings yourself.', 'muted'));
    }
    apply.onclick = async () => {
        if (!callbacks.isCurrent()) { notice('The case or form changed. Request a fresh suggestion.', true); return; }
        if (apply.disabled) return;
        busy = true;
        refreshApply();
        try { await callbacks.onApply(impact.select.value, urgency.select.value, context.clarifications); }
        catch (error) { notice(error.message, true); }
        finally { busy = false; refreshApply(); }
    };
    refreshApply();
    container.append(confirmation, help, apply);
    if (suggestion.investigation_questions?.length) {
        const optional = el('details'); optional.append(el('summary', 'Optional investigation questions'));
        suggestion.investigation_questions.forEach(q => optional.append(el('p', q)));
        container.append(optional);
    }
}
async function loadCases() {
    const cases = await api('/cases?view=' + queueView);
    const container = $('#cases');
    container.replaceChildren();
    $('#count').textContent = `(${cases.length})`;
    if (!cases.length) container.append(el('p', 'No cases in this view.', 'muted'));
    cases.sort((a, b) => a.priority.localeCompare(b.priority)).forEach(c => {
        const row = el('button', undefined, 'case-row');
        row.type = 'button';
        row.setAttribute('aria-pressed', String(c.unique_id === selectedId));
        const top = el('div', undefined, 'case-top');
        top.append(el('strong', c.customer_name), badge(c.priority));
        row.append(top,
            el('small', c.issue_description.length > 130 ? c.issue_description.slice(0, 130) + '…' : c.issue_description),
            el('small', `${c.status || 'Open'} · ${c.unique_id}`));
        row.onclick = () => openCase(c.unique_id);
        row.dataset.caseId = c.unique_id;
        container.append(row);
    });
}
async function openCase(id) {
    selectedId = id;
    try {
        const c = await api(`/cases/${encodeURIComponent(id)}`);
        if (selectedId !== id) return;
        document.querySelectorAll('.case-row').forEach(node =>
            node.setAttribute('aria-pressed', String(node.dataset.caseId === id)));
        const panel = $('#detail');
        panel.replaceChildren(badge(c.priority), el('h3', c.customer_name), el('small', c.unique_id), el('p', c.issue_description, 'description'));
        panel.append(el('p', c.priority_explanation, 'muted'));
        const controls = el('div', undefined, 'clarification-actions');
        async function mutate(path, method, data) {
            try { await api(`/cases/${encodeURIComponent(id)}${path}`, jsonOptions(method, {expected_revision:c.revision, ...data})); await loadCases(); await openCase(id); notice('Case updated.'); }
            catch(error) { notice(error.message, true); }
        }
        const action = (title, fn) => { const b=el('button',title,'secondary'); b.type='button'; b.onclick=fn; controls.append(b); };
        if(c.deleted_at) action('Restore to Resolved',()=>mutate('/restore','POST',{}));
        else {
            if(c.status !== 'Resolved') {
                if(c.status === 'Open') action('Start work',()=>mutate('/status','PATCH',{status:'In progress'}));
                action('Resolve case',()=>mutate('/status','PATCH',{status:'Resolved'}));
            } else action('Reopen case',()=>mutate('/status','PATCH',{status:'Open'}));
            action('Move to Trash',()=>{
                const dialog=el('dialog'); dialog.append(el('h3','Move this demo case to Trash?'),el('p','It will leave the queue. You can restore it from the Trash view.'));
                const cancel=el('button','Cancel','secondary'), remove=el('button','Move to Trash');
                cancel.onclick=()=>dialog.close(); remove.onclick=async()=>{dialog.close();await mutate('','DELETE',{confirmation:id});};
                dialog.append(cancel,remove); dialog.onclose=()=>dialog.remove(); document.body.append(dialog);dialog.showModal();
            });
        }
        panel.append(el('p', 'Status: '+(c.deleted_at ? 'Trash' : c.status)), controls);
        const facts = el('dl');
        [['Customer tier', c.customer_tier], ['Business impact', c.business_impact], ['Time sensitivity', c.time_sensitivity]]
            .forEach(([key, value]) => facts.append(el('dt', key), el('dd', value)));
        const summaryButton = el('button', 'Generate AI summary');
        const summary = el('p', undefined, 'summary');
        summary.hidden = true;
        summary.setAttribute('aria-live', 'polite');
        summaryButton.onclick = async () => {
            summaryButton.disabled = true;
            summaryButton.textContent = 'Generating…';
            try {
                const data = await api(`/cases/${encodeURIComponent(id)}/summary`, {method: 'POST'});
                summary.textContent = data.summary;
                summary.hidden = false;
                notice('AI summary generated.');
            } catch (error) { notice(error.message, true); }
            finally { summaryButton.disabled = false; summaryButton.textContent = 'Generate AI summary'; }
        };
        const savedContext = el('div');
        renderClarifications(savedContext, c.clarifications || [], 'Saved clarification answers');
        const triageButton = el('button', 'Suggest triage');
        const review = el('div', undefined, 'triage-review');
        review.hidden = true;
        triageButton.onclick = async () => {
            triageButton.disabled = true;
            triageButton.textContent = 'Assessing issue…';
            try {
                const context = {issue_description: c.issue_description, customer_tier: c.customer_tier,
                    clarifications: c.clarifications || []};
                const suggestion = await api('/triage', jsonOptions('POST', context));
                if (selectedId !== id || !triageButton.isConnected) return;
                showSuggestion(review, suggestion, context, {
                    isCurrent: () => selectedId === id && triageButton.isConnected,
                    saveLabel: 'Save answers only',
                    onContext: () => {},
                    onSave: async notes => {
                        await api(`/cases/${encodeURIComponent(id)}/clarifications`, jsonOptions('PATCH', {
                            expected_revision: c.revision, clarifications: notes, expected_clarifications: c.clarifications || [],
                            expected_issue_description: c.issue_description
                        }));
                        if (selectedId === id) await openCase(id);
                        notice('Answers saved. Original description and case ratings are unchanged.');
                    },
                    onApply: async (impact, urgency, notes) => {
                        await api(`/cases/${encodeURIComponent(id)}/triage`, jsonOptions('PATCH', {
                            business_impact: impact, time_sensitivity: urgency,
                            expected_business_impact: c.business_impact,
                            expected_time_sensitivity: c.time_sensitivity,
                            expected_issue_description: c.issue_description,
                            expected_revision: c.revision, clarifications: notes, expected_clarifications: c.clarifications || []
                        }));
                        await loadCases();
                        if (selectedId === id) await openCase(id);
                        notice('Reviewed triage and answers saved. Priority recalculated.');
                    }
                });
                notice('AI suggestions ready for review. No case changes have been saved.');
            } catch (error) { notice(error.message, true); }
            finally { triageButton.disabled = false; triageButton.textContent = 'Suggest triage'; }
        };
        if(c.deleted_at || c.status === 'Resolved') { panel.append(facts,savedContext,el('p','Reopen or restore this case before assessing it.','muted')); return; }
        panel.append(facts, savedContext, el('h3', 'AI triage assistant'),
            el('p', 'Get evidence-based suggestions, questions, and a next action. You decide what to apply.', 'muted'),
            triageButton, review, el('h3', 'AI summary'), summaryButton, summary);
    } catch (error) { notice(error.message, true); }
}
const form = $('#case-form');
const intakeReview = $('#intake-review');
function invalidateIntake() {
    intakeVersion++;
    intakeReview.hidden = true;
    intakeReview.replaceChildren();
    intakeReview.dataset.pendingAnswers = '';
    renderClarifications($('#intake-context'), intakeClarifications, 'Clarification answers to save with this case');
}
function handleFormEdit(event) {
    if (event.target.name) invalidateIntake();
}
form.addEventListener('input', handleFormEdit);
form.addEventListener('change', handleFormEdit);
$('#suggest-intake').onclick = async () => {
    const button = $('#suggest-intake');
    const description = form.elements.issue_description.value.trim();
    const tier = form.elements.customer_tier.value;
    if (!description) { notice('Describe the issue before requesting AI triage.', true); return; }
    const version = intakeVersion;
    button.disabled = true;
    button.textContent = 'Assessing issue…';
    try {
        const context = {issue_description: description, customer_tier: tier, clarifications: intakeClarifications};
        const suggestion = await api('/triage', jsonOptions('POST', context));
        if (version !== intakeVersion) { notice('The form changed. Request a fresh suggestion.', true); return; }
        showSuggestion(intakeReview, suggestion, context, {
            isCurrent: () => version === intakeVersion,
            applyLabel: 'Save reviewed case',
            onContext: notes => { intakeClarifications = notes; },
            onApply: async (impact, urgency, notes) => {
                intakeClarifications = notes;
                form.elements.business_impact.value = impact;
                form.elements.time_sensitivity.value = urgency;
                if (!form.reportValidity()) return;
                await saveIntake();
            }
        });
        notice('AI suggestions ready for review. Your form choices are unchanged.');
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; button.textContent = 'Suggest triage'; }
};
async function saveIntake() {
    if (intakeReview.dataset.pendingAnswers === 'true') { notice('Reassess with your answers or keep them in the form before creating the case.', true); return; }
    const button = $('#create-case');
    const data = Object.fromEntries(new FormData(form));
    data.clarifications = intakeClarifications;
    data.customer_name = data.customer_name.trim();
    data.issue_description = data.issue_description.trim();
    if (!data.customer_name || !data.issue_description) { notice('Enter a customer name and issue description.', true); return; }
    button.disabled = true;
    try {
        const c = await api('/cases', jsonOptions('POST', data));
        form.reset();
        intakeClarifications = [];
        invalidateIntake();
        selectedId = c.unique_id;
        queueView = 'active'; $('#queue-view').value = 'active';
        notice(`Case created successfully · ${c.priority} ${labels[c.priority]}`);
        await loadCases();
        await openCase(c.unique_id);
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; }
}
form.onsubmit = async event => { event.preventDefault(); await saveIntake(); };
$('#refresh').onclick = async () => {
    try { await loadCases(); notice('Case queue refreshed.'); }
    catch (error) { notice(error.message, true); }
};
loadCases().catch(error => {
    $('#cases').textContent = 'Unable to load cases. Use Refresh to try again.';
    notice(error.message, true);
});

$('#queue-view').onchange = async event => {queueView=event.target.value; selectedId=null; $('#detail').replaceChildren(el('h2','Case details'),el('p','Select a case.'));try {await loadCases();} catch(error){notice(error.message,true);} };
api('/demo-config').then(config=>{if(config.demo_mode){$('#demo-banner').hidden=false; $('#demo-banner').textContent=`Shared portfolio demo — fictional data only. Everyone shares this queue and can resolve or trash entries. Limits: ${config.limits.ai_per_day} AI requests/day, ${config.limits.creates_per_day} new cases/day. No private customer information.`;}}).catch(()=>{});

const manualAssessment = el('details');
manualAssessment.append(el('summary','Manual assessment — save without AI'));
manualAssessment.append(form.elements.business_impact.closest('label'),form.elements.time_sensitivity.closest('label'),$('#create-case'));
form.append(manualAssessment);
