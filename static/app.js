const $ = selector => document.querySelector(selector);
let selectedId = null;
let intakeVersion = 0;
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
    values.forEach(value => {
        const option = el('option', value);
        option.value = value;
        select.append(option);
    });
    select.value = value;
    label.append(select);
    return {label, select};
}
function showSuggestion(container, suggestion, current, onApply, isCurrent) {
    container.replaceChildren();
    container.hidden = false;
    container.append(el('h3', 'Review AI suggestions'),
        el('p', 'AI can be wrong. Check the evidence, edit the choices, then apply. Customer tier stays unchanged.', 'muted'));
    for (const [title, value, reason, evidence] of [
        ['Business impact', suggestion.business_impact, suggestion.impact_reason, suggestion.impact_evidence],
        ['Time sensitivity', suggestion.time_sensitivity, suggestion.urgency_reason, suggestion.urgency_evidence]
    ]) {
        container.append(el('h4', `${title}: ${value || 'Needs clarification'}`), el('p', reason));
        evidence.forEach(quote => container.append(el('blockquote', quote)));
    }
    if (suggestion.suggested_priority) {
        container.append(el('p', `Rule-based preview: ${suggestion.suggested_priority} · ${labels[suggestion.suggested_priority]}. Recalculated when you apply your reviewed choices.`, 'muted'));
    }
    if (suggestion.missing_information.length) {
        const list = el('ul');
        suggestion.missing_information.forEach(question => list.append(el('li', question)));
        container.append(el('h4', 'Questions to ask'), list);
    }
    container.append(el('h4', 'Suggested next action'), el('p', suggestion.next_action));
    const impact = ratingSelect('Reviewed business impact', impacts, suggestion.business_impact || current.business_impact);
    const urgency = ratingSelect('Reviewed time sensitivity', urgencies, suggestion.time_sensitivity || current.time_sensitivity);
    const fields = el('div', undefined, 'review-fields');
    fields.append(impact.label, urgency.label);
    const confirmed = el('input');
    confirmed.type = 'checkbox';
    const confirmation = el('label', undefined, 'review-confirm');
    confirmation.append(confirmed, el('span', 'I reviewed both ratings, including any choice the AI could not determine.'));
    const apply = el('button', 'Apply reviewed choices');
    apply.type = 'button';
    apply.disabled = true;
    confirmed.onchange = () => { apply.disabled = !confirmed.checked; };
    impact.select.onchange = urgency.select.onchange = () => {
        confirmed.checked = false;
        apply.disabled = true;
    };
    apply.onclick = async () => {
        if (!isCurrent()) { notice('The issue or customer tier changed. Request a new suggestion.', true); return; }
        apply.disabled = true;
        try { await onApply(impact.select.value, urgency.select.value); }
        catch (error) { notice(error.message, true); apply.disabled = false; }
    };
    container.append(fields);
    if (!suggestion.business_impact || !suggestion.time_sensitivity) {
        container.append(el('p', 'For any unanswered rating, the dropdown retains your current choice. Confirm it yourself or gather more information before applying.', 'muted'));
    }
    container.append(confirmation, apply);
}
async function loadCases() {
    const cases = await api('/cases');
    const container = $('#cases');
    container.replaceChildren();
    $('#count').textContent = `(${cases.length})`;
    if (!cases.length) container.append(el('p', 'Your queue is clear. Create your first case below.', 'muted'));
    cases.sort((a, b) => a.priority.localeCompare(b.priority)).forEach(c => {
        const row = el('button', undefined, 'case-row');
        row.type = 'button';
        row.setAttribute('aria-pressed', String(c.unique_id === selectedId));
        const top = el('div', undefined, 'case-top');
        top.append(el('strong', c.customer_name), badge(c.priority));
        row.append(top,
            el('small', c.issue_description.length > 130 ? c.issue_description.slice(0, 130) + '…' : c.issue_description),
            el('small', c.unique_id));
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
        const triageButton = el('button', 'Suggest triage');
        const review = el('div', undefined, 'triage-review');
        review.hidden = true;
        triageButton.onclick = async () => {
            triageButton.disabled = true;
            triageButton.textContent = 'Assessing issue…';
            try {
                const suggestion = await api('/triage', jsonOptions('POST', {
                    issue_description: c.issue_description, customer_tier: c.customer_tier
                }));
                if (selectedId !== id || !triageButton.isConnected) return;
                showSuggestion(review, suggestion, c, async (impact, urgency) => {
                    await api(`/cases/${encodeURIComponent(id)}/triage`, jsonOptions('PATCH', {
                        business_impact: impact, time_sensitivity: urgency,
                        expected_business_impact: c.business_impact,
                        expected_time_sensitivity: c.time_sensitivity,
                        expected_issue_description: c.issue_description
                    }));
                    await loadCases();
                    if (selectedId === id) await openCase(id);
                    notice('Reviewed triage saved. Priority recalculated using the existing rules.');
                }, () => selectedId === id && triageButton.isConnected);
                notice('AI suggestions ready for review. No case changes have been saved.');
            } catch (error) { notice(error.message, true); }
            finally { triageButton.disabled = false; triageButton.textContent = 'Suggest triage'; }
        };
        panel.append(facts, el('h3', 'AI triage assistant'),
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
        const suggestion = await api('/triage', jsonOptions('POST', {issue_description: description, customer_tier: tier}));
        if (version !== intakeVersion) { notice('The form changed. Request a fresh suggestion.', true); return; }
        showSuggestion(intakeReview, suggestion, {
            business_impact: form.elements.business_impact.value,
            time_sensitivity: form.elements.time_sensitivity.value
        }, async (impact, urgency) => {
            form.elements.business_impact.value = impact;
            form.elements.time_sensitivity.value = urgency;
            invalidateIntake();
            notice('Reviewed choices added to the form. Click Create case when ready.');
        }, () => version === intakeVersion);
        notice('AI suggestions ready for review. Your form choices are unchanged.');
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; button.textContent = 'Suggest triage'; }
};
form.onsubmit = async event => {
    event.preventDefault();
    const button = $('#create-case');
    const data = Object.fromEntries(new FormData(form));
    data.customer_name = data.customer_name.trim();
    data.issue_description = data.issue_description.trim();
    if (!data.customer_name || !data.issue_description) { notice('Enter a customer name and issue description.', true); return; }
    button.disabled = true;
    try {
        const c = await api('/cases', jsonOptions('POST', data));
        form.reset();
        invalidateIntake();
        selectedId = c.unique_id;
        notice(`Case created successfully · ${c.priority} ${labels[c.priority]}`);
        await loadCases();
        await openCase(c.unique_id);
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; }
};
$('#refresh').onclick = async () => {
    try { await loadCases(); notice('Case queue refreshed.'); }
    catch (error) { notice(error.message, true); }
};
loadCases().catch(error => {
    $('#cases').textContent = 'Unable to load cases. Use Refresh to try again.';
    notice(error.message, true);
});
