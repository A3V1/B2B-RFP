let currentRfpId = null, currentFile = null, analysisData = null;
let rfpList = JSON.parse(localStorage.getItem('rfpList') || '[]');

document.addEventListener('DOMContentLoaded', () => { renderRfpHistory(); setupUpload(); });

function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(`view-${viewName}`).classList.add('active');
    document.querySelector(`.nav-item[onclick="showView('${viewName}')"]`).classList.add('active');
}

function setupUpload() {
    const zone = document.getElementById('uploadZone'), input = document.getElementById('fileInput');
    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('dragover'); handleFile(e.dataTransfer.files[0]); });
    input.addEventListener('change', e => handleFile(e.target.files[0]));
}

function handleFile(file) {
    if (!file || !file.name.match(/\.(pdf|docx|doc)$/i)) { showToast('Invalid file type. Use PDF or DOCX', 'error'); return; }
    currentFile = file;
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = (file.size / 1024 / 1024).toFixed(2) + ' MB';
    document.getElementById('filePreview').classList.remove('hidden');
    document.getElementById('uploadBtn').disabled = false;
}

function clearFile() {
    currentFile = null;
    document.getElementById('filePreview').classList.add('hidden');
    document.getElementById('uploadBtn').disabled = true;
    document.getElementById('fileInput').value = '';
}

async function uploadFile() {
    if (!currentFile) return;
    const btn = document.getElementById('uploadBtn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Uploading...';

    try {
        const formData = new FormData();
        formData.append('file', currentFile);
        const uploadRes = await fetch('/api/v1/upload', { method: 'POST', body: formData });
        if (!uploadRes.ok) throw new Error('Upload failed');
        const uploadData = await uploadRes.json();

        btn.innerHTML = '<div class="spinner"></div> Extracting text...';
        const extractRes = await fetch(`/api/v1/extract?rfp_id=${uploadData.rfp_id}`, { method: 'POST' });
        if (!extractRes.ok) throw new Error('Extraction failed');

        currentRfpId = uploadData.rfp_id;
        rfpList.unshift({ id: currentRfpId, name: currentFile.name, date: new Date().toISOString(), status: 'uploaded' });
        localStorage.setItem('rfpList', JSON.stringify(rfpList.slice(0, 10)));
        renderRfpHistory();
        showToast('File uploaded successfully!', 'success');
        clearFile();
        showView('analyze');
    } catch (error) { showToast(error.message, 'error'); }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-upload"></i> Upload & Extract';
}

function renderRfpHistory() {
    const container = document.getElementById('rfpHistory');
    if (rfpList.length === 0) { container.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 20px;">No RFPs uploaded yet</div>'; return; }
    container.innerHTML = rfpList.map(rfp => `
        <div class="rfp-item ${currentRfpId === rfp.id ? 'active' : ''}" onclick="selectRfp('${rfp.id}')">
            <div class="rfp-item-name">${rfp.name}</div>
            <div class="rfp-item-meta"><span>${new Date(rfp.date).toLocaleDateString()}</span><span class="rfp-status status-${rfp.status}">${rfp.status}</span></div>
        </div>
    `).join('');
}

function selectRfp(id) { currentRfpId = id; renderRfpHistory(); showView('analyze'); }

const agents = ['parser', 'analyzer', 'matcher', 'scorer', 'response'];

function setAgentState(index, state) {
    agents.forEach((agent, i) => {
        const node = document.getElementById(`agent-${agent}`);
        node.classList.remove('waiting', 'active', 'completed', 'error');
        if (i < index) node.classList.add('completed');
        else if (i === index) node.classList.add(state);
        else node.classList.add('waiting');
    });
}

function addLog(message, type = 'info') {
    const log = document.getElementById('agentLog');
    const colors = { info: 'var(--text)', success: 'var(--success)', error: 'var(--danger)', warning: 'var(--orange)' };
    log.innerHTML += `<div style="color: ${colors[type]}; margin-bottom: 4px;">[${new Date().toLocaleTimeString()}] ${message}</div>`;
    log.scrollTop = log.scrollHeight;
}

async function runAnalysis() {
    if (!currentRfpId) { showToast('Please select or upload an RFP first', 'error'); return; }
    const btn = document.getElementById('analyzeBtn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Analyzing...';
    document.getElementById('agentLog').innerHTML = '';
    document.getElementById('analysisStatus').innerHTML = '<div class="spinner"></div> Starting analysis...';

    for (let i = 0; i < agents.length; i++) {
        setAgentState(i, 'active');
        addLog(`Running ${agents[i]} agent...`, 'info');
        document.getElementById('analysisStatus').innerHTML = `<div style="font-size: 18px;">🤖 ${agents[i].charAt(0).toUpperCase() + agents[i].slice(1)} Agent</div><div style="color: var(--text-muted); margin-top: 8px;">Processing...</div>`;
        await new Promise(r => setTimeout(r, 400));
    }

    try {
        const res = await fetch(`/api/v1/analyze/sync?rfp_id=${currentRfpId}`, { method: 'POST' });
        analysisData = await res.json();
        setAgentState(agents.length, 'completed');
        addLog('Analysis complete!', 'success');

        const rfp = rfpList.find(r => r.id === currentRfpId);
        if (rfp) { rfp.status = analysisData.errors?.length > 0 ? 'error' : 'analyzed'; localStorage.setItem('rfpList', JSON.stringify(rfpList)); renderRfpHistory(); }

        updateResults(analysisData);
        document.getElementById('analysisStatus').innerHTML = '<div style="color: var(--success); font-size: 18px;"><i class="fas fa-check-circle"></i> Analysis Complete</div>';
        if (analysisData.errors?.length > 0) analysisData.errors.forEach(e => addLog(e, 'error'));
        showToast('Analysis complete!', 'success');
    } catch (error) {
        setAgentState(0, 'error');
        addLog(error.message, 'error');
        document.getElementById('analysisStatus').innerHTML = `<div style="color: var(--danger);"><i class="fas fa-times-circle"></i> Error: ${error.message}</div>`;
        showToast(error.message, 'error');
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-play"></i> Start Analysis';
}

function updateResults(data) {
    document.getElementById('stat-sections').textContent = data.analysis?.sections_found || 0;
    document.getElementById('stat-requirements').textContent = data.analysis?.requirements_extracted || 0;
    document.getElementById('stat-matched').textContent = data.analysis?.requirements_matched || 0;
    document.getElementById('stat-score').textContent = Math.round(data.scoring?.overall_score || 0) + '%';

    const score = data.scoring?.overall_score || 0;
    document.getElementById('scoreCircle').style.setProperty('--score', score);
    document.getElementById('scoreValue').textContent = Math.round(score) + '%';
    document.getElementById('scoreLabel').textContent = score >= 70 ? 'Good Match' : score >= 40 ? 'Partial Match' : 'Low Match';

    const recs = data.scoring?.recommendations || [];
    document.getElementById('recommendationsList').innerHTML = recs.length > 0 ? recs.map(r => `<div class="result-item"><div class="result-desc">• ${r}</div></div>`).join('') : '<div style="color: var(--text-muted); text-align: center;">No recommendations</div>';

    const matches = data.matches || [];
    document.getElementById('matchesList').innerHTML = matches.length > 0 ? matches.map(m => `
        <div class="result-item">
            <div class="result-header"><span class="result-title">${m.requirement_id}</span><span class="result-score">${m.coverage_score || 0}%</span></div>
            <div class="result-desc"><strong>Requirement:</strong> ${m.requirement_description}<br><strong>Best Match:</strong> ${m.best_match?.name || 'No match'}</div>
        </div>
    `).join('') : '<div style="color: var(--text-muted); text-align: center;">No matches found</div>';

    document.getElementById('proposalSummary').textContent = data.proposal?.summary || 'No summary generated';
    document.getElementById('technicalResponse').textContent = data.proposal?.technical || 'No technical response';
    document.getElementById('commercialResponse').textContent = data.proposal?.commercial || 'No commercial response';
}

function showResultTab(tab) {
    document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab[onclick="showResultTab('${tab}')"]`).classList.add('active');
    document.getElementById(`rtab-${tab}`).classList.add('active');
}

function exportResults(format) {
    if (!analysisData) { showToast('No data to export', 'error'); return; }
    downloadBlob(new Blob([JSON.stringify(analysisData, null, 2)], { type: 'application/json' }), `rfp_analysis_${currentRfpId}.json`);
}

function exportProposal(format) {
    if (!analysisData?.proposal) { showToast('No proposal to export', 'error'); return; }
    const content = `PROPOSAL SUMMARY\n${'='.repeat(50)}\n${analysisData.proposal.summary}\n\nTECHNICAL RESPONSE\n${'='.repeat(50)}\n${analysisData.proposal.technical}\n\nCOMMERCIAL RESPONSE\n${'='.repeat(50)}\n${analysisData.proposal.commercial}`;
    downloadBlob(new Blob([content], { type: 'text/plain' }), `rfp_proposal_${currentRfpId}.txt`);
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast'), icon = toast.querySelector('i');
    document.getElementById('toastMessage').textContent = message;
    toast.className = `toast show ${type}`;
    icon.className = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
    setTimeout(() => toast.classList.remove('show'), 3000);
}
