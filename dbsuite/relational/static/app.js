const views = {
    erd: { viewport: document.getElementById('erdViewport'), canvas: document.getElementById('erdDiagramCanvas'), scale: 1, x: 40, y: 40 },
    mapper: { viewport: document.getElementById('viewport'), canvas: document.getElementById('diagramCanvas'), scale: 1, x: 40, y: 40 }
};

function setStatus(message, type, panel) {
    const element = document.getElementById(`${panel}Status`);
    element.textContent = message;
    element.className = `status ${type}`;
    element.hidden = !message;
}

function applyTransform(view) {
    view.canvas.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`;
}

function resetView(view) {
    view.scale = 1;
    view.x = 40;
    view.y = 40;
    applyTransform(view);
}

function zoom(view, step) {
    if (step === 'reset') return resetView(view);
    view.scale = Math.min(5, Math.max(0.1, view.scale * (step === 'in' ? 1.25 : 0.8)));
    applyTransform(view);
}

for (const view of Object.values(views)) {
    let dragging = false;
    let startX = 0;
    let startY = 0;
    view.viewport.addEventListener('pointerdown', event => {
        if (event.button !== 0) return;
        dragging = true;
        view.viewport.setPointerCapture(event.pointerId);
        startX = event.clientX - view.x;
        startY = event.clientY - view.y;
    });
    view.viewport.addEventListener('pointermove', event => {
        if (!dragging) return;
        view.x = event.clientX - startX;
        view.y = event.clientY - startY;
        applyTransform(view);
    });
    view.viewport.addEventListener('pointerup', () => { dragging = false; });
    view.viewport.addEventListener('pointercancel', () => { dragging = false; });
    view.viewport.addEventListener('wheel', event => {
        event.preventDefault();
        const nextScale = Math.min(5, Math.max(0.1, view.scale * (event.deltaY < 0 ? 1.15 : 0.87)));
        const bounds = view.viewport.getBoundingClientRect();
        const x = event.clientX - bounds.left;
        const y = event.clientY - bounds.top;
        view.x = x - (x - view.x) * nextScale / view.scale;
        view.y = y - (y - view.y) * nextScale / view.scale;
        view.scale = nextScale;
        applyTransform(view);
    }, { passive: false });
}

async function renderDiagram(dot, viewName, engine = 'dot') {
    const view = views[viewName];
    try {
        const viz = await Viz.instance();
        const svg = viz.renderSVGElement(dot, { engine });
        view.canvas.replaceChildren(svg);
        const infoId = viewName === 'erd' ? 'erdDiagramInfo' : 'diagramInfo';
        document.getElementById(infoId).textContent = `Rendered (${engine})`;
        resetView(view);
    } catch (error) {
        throw new Error(`Failed to render diagram: ${error.message}`);
    }
}

const samplePrompt = 'A university database tracks Students and Courses. A Student has a StudentID (primary key), Name, and Email. A Course has a CourseID (primary key), Title, and Credits. Students enroll in Courses (many-to-many, total participation). Courses have Prerequisites as a weak entity identified by PrereqOrder (partial key) and Notes, connected via Has_Prerequisite.';
document.getElementById('btnSamplePrompt').addEventListener('click', () => {
    document.getElementById('descInput').value = samplePrompt;
});

async function requestDiagram(url, payload, panel, button, viewName, engine = 'dot') {
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Working…';
    setStatus('Preparing diagram…', 'loading', panel);
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Request failed. Check the input and try again.');
        if (viewName === 'erd') document.getElementById('erdJsonInput').value = data.json;
        else document.getElementById('schemaOutput').textContent = JSON.stringify(data.schema, null, 2);
        await renderDiagram(data.dot, viewName, engine);
        setStatus('', '', panel);
    } catch (error) {
        setStatus(error.message, 'error', panel);
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

document.getElementById('btnGenerate').addEventListener('click', () => {
    const description = document.getElementById('descInput').value.trim();
    if (!description) return setStatus('Enter a database description first.', 'error', 'erd');
    requestDiagram('/api/generate', { description }, 'erd', document.getElementById('btnGenerate'), 'erd', document.getElementById('engineSelect').value);
});

document.getElementById('btnErdRender').addEventListener('click', () => {
    const json = document.getElementById('erdJsonInput').value.trim();
    if (!json) return setStatus('Enter ER schema JSON first.', 'error', 'erd');
    requestDiagram('/api/render', { json }, 'erd', document.getElementById('btnErdRender'), 'erd', document.getElementById('engineSelect').value);
});

document.getElementById('engineSelect').addEventListener('change', async () => {
    const svg = views.erd.canvas.querySelector('svg');
    if (!svg) return;
    const text = document.getElementById('erdJsonInput').value.trim();
    if (!text) return;
    try {
        const data = await fetch('/api/render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ json: text }) }).then(response => response.json());
        if (data.dot) await renderDiagram(data.dot, 'erd', document.getElementById('engineSelect').value);
    } catch (error) {
        setStatus(error.message, 'error', 'erd');
    }
});

async function copyText(text, panel) {
    if (!text) return setStatus('There is no JSON to copy yet.', 'error', panel);
    try {
        await navigator.clipboard.writeText(text);
        setStatus('JSON copied to clipboard.', 'loading', panel);
        setTimeout(() => setStatus('', '', panel), 1800);
    } catch {
        setStatus('Clipboard access was blocked. Select and copy the JSON manually.', 'error', panel);
    }
}
document.getElementById('btnErdCopy').addEventListener('click', () => copyText(document.getElementById('erdJsonInput').value, 'erd'));
document.getElementById('btnCopy').addEventListener('click', () => copyText(document.getElementById('jsonInput').value, 'mapper'));

document.getElementById('btnRender').addEventListener('click', () => {
    const json = document.getElementById('jsonInput').value.trim();
    if (!json) return setStatus('Enter ER schema JSON first.', 'error', 'mapper');
    requestDiagram('/api/convert', { json }, 'mapper', document.getElementById('btnRender'), 'mapper');
});

async function loadJsonFile(input, targetId, panel) {
    if (!input.files.length) return;
    try {
        const text = await input.files[0].text();
        JSON.parse(text);
        document.getElementById(targetId).value = text;
        setStatus('', '', panel);
    } catch (error) {
        setStatus(`Invalid JSON file: ${error.message}`, 'error', panel);
    }
}
document.getElementById('erdFile').addEventListener('change', event => loadJsonFile(event.target, 'jsonInput', 'mapper'));
document.getElementById('datasetFile').addEventListener('change', event => loadJsonFile(event.target, 'datasetsInput', 'queries'));

document.getElementById('btnQuery').addEventListener('click', async () => {
    const button = document.getElementById('btnQuery');
    const output = document.getElementById('queryResult');
    button.disabled = true;
    setStatus('Executing query…', 'loading', 'queries');
    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ datasets: document.getElementById('datasetsInput').value, expression: document.getElementById('expressionInput').value })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Query failed. Check the dataset and expression.');
        const table = document.createElement('table');
        const header = table.createTHead().insertRow();
        for (const column of data.columns) {
            const cell = document.createElement('th');
            cell.textContent = column;
            header.appendChild(cell);
        }
        const body = table.createTBody();
        for (const row of data.rows) {
            const tr = body.insertRow();
            for (const column of data.columns) {
                const cell = tr.insertCell();
                cell.textContent = row[column] == null ? '' : String(row[column]);
            }
        }
        const count = document.createElement('p');
        count.textContent = `${data.rows.length} row(s)`;
        output.replaceChildren(table, count);
        setStatus('', '', 'queries');
    } catch (error) {
        setStatus(error.message, 'error', 'queries');
    } finally {
        button.disabled = false;
    }
});

document.querySelectorAll('[data-zoom]').forEach(button => button.addEventListener('click', () => zoom(views[button.dataset.zoom], button.dataset.step)));
document.getElementById('btnZoomIn').addEventListener('click', () => zoom(views.mapper, 'in'));
document.getElementById('btnZoomOut').addEventListener('click', () => zoom(views.mapper, 'out'));
document.getElementById('btnReset').addEventListener('click', () => zoom(views.mapper, 'reset'));

const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectTab(tab) {
    for (const item of tabs) {
        const selected = item === tab;
        item.setAttribute('aria-selected', String(selected));
        item.tabIndex = selected ? 0 : -1;
        document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
    }
}
for (const tab of tabs) {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
        let index = tabs.indexOf(tab);
        if (event.key === 'ArrowRight') index = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') index = (index - 1 + tabs.length) % tabs.length;
        else if (event.key === 'Home') index = 0;
        else if (event.key === 'End') index = tabs.length - 1;
        else return;
        event.preventDefault();
        selectTab(tabs[index]);
        tabs[index].focus();
    });
}
