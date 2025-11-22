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
        const extractData = await extractRes.json();

        currentRfpId = uploadData.rfp_id;
        rfpList.unshift({ id: currentRfpId, name: currentFile.name, date: new Date().toISOString(), status: 'uploaded' });
        localStorage.setItem('rfpList', JSON.stringify(rfpList.slice(0, 10)));
        renderRfpHistory();

        // Display extracted text preview
        displayExtractedText(extractData.text);

        showToast('File uploaded and text extracted successfully!', 'success');
        clearFile();
    } catch (error) { showToast(error.message, 'error'); }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-upload"></i> Upload & Extract';
}

function displayExtractedText(text) {
    const card = document.getElementById('extractedTextCard');
    const preview = document.getElementById('extractedTextPreview');
    const stats = document.getElementById('textStats');

    // Calculate stats
    const charCount = text.length;
    const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
    const lineCount = text.split('\n').length;

    stats.textContent = `${wordCount.toLocaleString()} words | ${charCount.toLocaleString()} characters | ${lineCount.toLocaleString()} lines`;
    preview.textContent = text;
    card.classList.remove('hidden');

    // Scroll to the extracted text card
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function proceedToAnalysis() {
    if (!currentRfpId) {
        showToast('No RFP selected. Please upload a document first.', 'error');
        return;
    }
    // Hide the extracted text card for next upload
    document.getElementById('extractedTextCard').classList.add('hidden');
    showView('analyze');
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
    // Update stats cards
    document.getElementById('stat-sections').textContent = data.analysis?.sections_found || 0;
    document.getElementById('stat-requirements').textContent = data.analysis?.requirements_extracted || 0;
    document.getElementById('stat-matched').textContent = data.analysis?.requirements_matched || 0;
    document.getElementById('stat-score').textContent = Math.round(data.scoring?.overall_score || 0) + '%';

    // Update score circle
    const score = data.scoring?.overall_score || 0;
    document.getElementById('scoreCircle').style.setProperty('--score', score);
    document.getElementById('scoreValue').textContent = Math.round(score) + '%';
    document.getElementById('scoreLabel').textContent = score >= 70 ? 'Good Match' : score >= 40 ? 'Partial Match' : 'Low Match';

    // Update Score Breakdown in Overview tab
    const breakdown = data.scoring?.breakdown || {};
    const breakdownHtml = Object.keys(breakdown).length > 0 ? Object.entries(breakdown).map(([key, val]) => `
        <div class="result-item" style="margin-bottom: 12px;">
            <div class="result-header">
                <span class="result-title">${formatLabel(key)}</span>
                <span class="result-score">${val.weighted_score?.toFixed(1) || val.score || 0}/${val.max || 100}</span>
            </div>
            <div class="result-desc" style="font-size: 12px; color: var(--text-muted);">${val.notes || ''}</div>
            <div style="background: var(--navy); border-radius: 4px; height: 6px; margin-top: 8px; overflow: hidden;">
                <div style="background: var(--orange); height: 100%; width: ${((val.weighted_score || val.score || 0) / (val.max || 100)) * 100}%;"></div>
            </div>
        </div>
    `).join('') : '<div style="color: var(--text-muted);">No breakdown available</div>';
    document.getElementById('scoreBreakdown').innerHTML = breakdownHtml;

    // Update Requirements tab - show extracted requirements with their specifications
    const matches = data.matches || [];
    const requirementsHtml = matches.length > 0 ? matches.map((m, i) => {
        const specs = m.best_match ? Object.entries(m.best_match.matched_specs || {}).map(([k, v]) =>
            `<span class="spec-tag ${v ? 'matched' : 'unmatched'}">${formatLabel(k)}: ${v ? '✓' : '✗'}</span>`
        ).join('') : '';

        return `
        <div class="result-item" style="margin-bottom: 16px; padding: 16px; background: var(--navy); border-radius: 8px;">
            <div class="result-header" style="margin-bottom: 8px;">
                <span class="result-title" style="font-size: 14px; font-weight: 600;">${m.requirement_id}</span>
                <span class="result-score" style="background: ${m.coverage_score >= 70 ? 'var(--success)' : m.coverage_score >= 40 ? 'var(--orange)' : 'var(--danger)'}; padding: 4px 10px; border-radius: 12px; font-size: 12px;">${m.coverage_score || 0}% match</span>
            </div>
            <div class="result-desc" style="margin-bottom: 10px; line-height: 1.5;">${m.requirement_description}</div>
            ${specs ? `<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;">${specs}</div>` : ''}
        </div>
    `}).join('') : '<div style="color: var(--text-muted); text-align: center; padding: 40px;">No requirements extracted</div>';
    document.getElementById('requirementsList').innerHTML = requirementsHtml;

    // Update Matches tab - show product matches
    const matchesHtml = matches.length > 0 ? matches.map(m => {
        const bestMatch = m.best_match;
        if (!bestMatch) {
            return `
            <div class="result-item" style="margin-bottom: 12px; padding: 16px; background: var(--navy); border-radius: 8px; border-left: 3px solid var(--danger);">
                <div class="result-header"><span class="result-title">${m.requirement_id}</span><span class="result-score" style="color: var(--danger);">No Match</span></div>
                <div class="result-desc">${m.requirement_description}</div>
            </div>`;
        }
        return `
        <div class="result-item" style="margin-bottom: 12px; padding: 16px; background: var(--navy); border-radius: 8px; border-left: 3px solid ${m.coverage_score >= 70 ? 'var(--success)' : 'var(--orange)'};">
            <div class="result-header" style="margin-bottom: 8px;">
                <span class="result-title">${m.requirement_id}</span>
                <span class="result-score">${m.coverage_score || 0}%</span>
            </div>
            <div class="result-desc" style="margin-bottom: 12px;"><strong>Requirement:</strong> ${m.requirement_description}</div>
            <div style="background: var(--black); padding: 12px; border-radius: 6px;">
                <div style="font-weight: 600; color: var(--orange); margin-bottom: 6px;">🏭 ${bestMatch.name}</div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; color: var(--text-muted);">
                    <div><strong>SKU:</strong> ${bestMatch.sku || 'N/A'}</div>
                    <div><strong>Manufacturer:</strong> ${bestMatch.manufacturer || 'N/A'}</div>
                    <div><strong>Price:</strong> ₹${bestMatch.price_per_meter?.toFixed(2) || '0.00'}/m</div>
                    <div><strong>In Stock:</strong> ${bestMatch.in_stock ? '<span style="color: var(--success);">Yes</span>' : '<span style="color: var(--danger);">No</span>'}</div>
                    <div><strong>Lead Time:</strong> ${bestMatch.lead_time_days || 'N/A'} days</div>
                    <div><strong>Match Score:</strong> ${bestMatch.score || m.coverage_score || 0}%</div>
                </div>
            </div>
        </div>
    `}).join('') : '<div style="color: var(--text-muted); text-align: center; padding: 40px;">No matches found</div>';
    document.getElementById('matchesList').innerHTML = matchesHtml;

    // Update Recommendations tab
    const recs = data.scoring?.recommendations || [];
    document.getElementById('recommendationsList').innerHTML = recs.length > 0 ? recs.map(r => {
        const type = r.toLowerCase().startsWith('pursue') ? 'success' :
                     r.toLowerCase().startsWith('gap') ? 'warning' :
                     r.toLowerCase().startsWith('risk') ? 'danger' : 'info';
        const icon = type === 'success' ? 'fa-check-circle' :
                     type === 'warning' ? 'fa-exclamation-triangle' :
                     type === 'danger' ? 'fa-times-circle' : 'fa-info-circle';
        return `
        <div class="result-item" style="margin-bottom: 10px; padding: 12px 16px; background: var(--navy); border-radius: 6px; border-left: 3px solid var(--${type === 'info' ? 'text-muted' : type});">
            <i class="fas ${icon}" style="color: var(--${type === 'info' ? 'text-muted' : type}); margin-right: 10px;"></i>
            ${r}
        </div>`;
    }).join('') : '<div style="color: var(--text-muted); text-align: center; padding: 40px;">No recommendations</div>';

    // Update unified Proposal document
    updateProposalDocument(data);
}

// Helper function to format labels (snake_case to Title Case)
function formatLabel(str) {
    return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Simple markdown renderer for proposal content
function renderMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/^### (.*$)/gim, '<h4 style="color: var(--orange); margin: 16px 0 8px 0;">$1</h4>')
        .replace(/^## (.*$)/gim, '<h3 style="color: var(--orange); margin: 20px 0 10px 0;">$1</h3>')
        .replace(/^# (.*$)/gim, '<h2 style="color: var(--orange); margin: 24px 0 12px 0;">$1</h2>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^\s*[-•]\s+(.*$)/gim, '<li style="margin-left: 20px; margin-bottom: 4px;">$1</li>')
        .replace(/^\|(.*)\|$/gim, (match, content) => {
            const cells = content.split('|').map(c => c.trim());
            return `<tr>${cells.map(c => `<td style="padding: 8px; border: 1px solid var(--navy);">${c}</td>`).join('')}</tr>`;
        })
        .replace(/\n/g, '<br>');
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

function updateProposalDocument(data) {
    const container = document.getElementById('proposalContent');
    if (!data.proposal?.summary && !data.proposal?.technical && !data.proposal?.commercial) {
        container.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 60px;">
                <i class="fas fa-file-alt" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                <div>No proposal generated</div>
            </div>`;
        return;
    }

    const rfpInfo = rfpList.find(r => r.id === currentRfpId);
    const currentDate = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    const score = data.scoring?.overall_score || 0;
    const matches = data.matches || [];
    const totalValue = matches.reduce((sum, m) => {
        if (m.best_match?.price_per_meter) {
            const qty = 1000; // Default quantity
            return sum + (m.best_match.price_per_meter * qty);
        }
        return sum;
    }, 0);

    container.innerHTML = `
        <div class="proposal-header">
            <div class="proposal-logo">
                <i class="fas fa-bolt"></i>
                <span>RFP RESPONSE</span>
            </div>
            <div class="proposal-meta">
                <div><strong>RFP Reference:</strong> ${rfpInfo?.name || 'N/A'}</div>
                <div><strong>Date:</strong> ${currentDate}</div>
                <div><strong>Match Score:</strong> <span class="score-badge ${score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low'}">${Math.round(score)}%</span></div>
            </div>
        </div>

        <div class="proposal-section">
            <h2 class="section-title"><i class="fas fa-file-signature"></i> Executive Summary</h2>
            <div class="section-content">${renderMarkdown(data.proposal?.summary || 'No summary available')}</div>
        </div>

        <div class="proposal-section">
            <h2 class="section-title"><i class="fas fa-cogs"></i> Technical Response</h2>
            <div class="section-content">${renderMarkdown(data.proposal?.technical || 'No technical response available')}</div>
        </div>

        <div class="proposal-section">
            <h2 class="section-title"><i class="fas fa-list-check"></i> Requirements Compliance Matrix</h2>
            <div class="section-content">
                <table class="compliance-table">
                    <thead>
                        <tr>
                            <th>Req. ID</th>
                            <th>Requirement</th>
                            <th>Proposed Product</th>
                            <th>Match</th>
                            <th>Unit Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${matches.map(m => `
                            <tr>
                                <td><strong>${m.requirement_id}</strong></td>
                                <td>${m.requirement_description?.substring(0, 50)}${m.requirement_description?.length > 50 ? '...' : ''}</td>
                                <td>${m.best_match?.name || '<span class="no-match">No match</span>'}</td>
                                <td><span class="match-badge ${m.coverage_score >= 70 ? 'high' : m.coverage_score >= 40 ? 'medium' : 'low'}">${m.coverage_score || 0}%</span></td>
                                <td>${m.best_match?.price_per_meter ? '₹' + m.best_match.price_per_meter.toFixed(2) + '/m' : '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="proposal-section">
            <h2 class="section-title"><i class="fas fa-rupee-sign"></i> Commercial Response</h2>
            <div class="section-content">${renderMarkdown(data.proposal?.commercial || 'No commercial response available')}</div>
        </div>

        <div class="proposal-section">
            <h2 class="section-title"><i class="fas fa-lightbulb"></i> Recommendations</h2>
            <div class="section-content">
                <ul class="recommendations-list">
                    ${(data.scoring?.recommendations || []).map(r => `<li>${r}</li>`).join('') || '<li>No recommendations</li>'}
                </ul>
            </div>
        </div>

        <div class="proposal-footer">
            <div class="footer-note">
                <i class="fas fa-robot"></i> This proposal was generated using AI-powered RFP analysis.
                <br>Please review all details before submission.
            </div>
            <div class="footer-summary">
                <div class="summary-item">
                    <span class="summary-label">Requirements Matched</span>
                    <span class="summary-value">${data.analysis?.requirements_matched || 0}/${data.analysis?.requirements_extracted || 0}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Overall Score</span>
                    <span class="summary-value">${Math.round(score)}%</span>
                </div>
            </div>
        </div>
    `;
}

function exportProposalPDF() {
    if (!analysisData?.proposal) {
        showToast('No proposal to export. Run analysis first.', 'error');
        return;
    }

    // Create a new window for printing
    const printWindow = window.open('', '_blank');
    const proposalContent = document.getElementById('proposalContent').innerHTML;
    const rfpInfo = rfpList.find(r => r.id === currentRfpId);

    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>RFP Proposal - ${rfpInfo?.name || 'Export'}</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 12pt;
                    line-height: 1.6;
                    color: #1a1a1a;
                    padding: 40px;
                    max-width: 800px;
                    margin: 0 auto;
                }
                .proposal-header {
                    border-bottom: 3px solid #ff6500;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                }
                .proposal-logo {
                    font-size: 24pt;
                    font-weight: bold;
                    color: #ff6500;
                }
                .proposal-logo i { margin-right: 10px; }
                .proposal-meta { text-align: right; font-size: 10pt; color: #666; }
                .proposal-meta div { margin-bottom: 4px; }
                .proposal-section {
                    margin-bottom: 30px;
                    page-break-inside: avoid;
                }
                .section-title {
                    font-size: 14pt;
                    color: #ff6500;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 8px;
                    margin-bottom: 16px;
                }
                .section-title i { margin-right: 8px; }
                .section-content {
                    color: #333;
                }
                .section-content h3, .section-content h4 {
                    color: #ff6500;
                    margin: 16px 0 8px 0;
                }
                .section-content ul, .section-content ol {
                    margin-left: 20px;
                }
                .section-content li {
                    margin-bottom: 6px;
                }
                .compliance-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 10pt;
                    margin: 16px 0;
                }
                .compliance-table th, .compliance-table td {
                    border: 1px solid #ddd;
                    padding: 8px 10px;
                    text-align: left;
                }
                .compliance-table th {
                    background: #f5f5f5;
                    font-weight: 600;
                    color: #333;
                }
                .compliance-table tr:nth-child(even) {
                    background: #fafafa;
                }
                .match-badge, .score-badge {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 9pt;
                    font-weight: 600;
                }
                .match-badge.high, .score-badge.high { background: #dcfce7; color: #166534; }
                .match-badge.medium, .score-badge.medium { background: #fef3c7; color: #92400e; }
                .match-badge.low, .score-badge.low { background: #fee2e2; color: #991b1b; }
                .no-match { color: #991b1b; font-style: italic; }
                .recommendations-list {
                    list-style: none;
                    padding: 0;
                }
                .recommendations-list li {
                    padding: 8px 12px;
                    margin-bottom: 8px;
                    background: #f5f5f5;
                    border-left: 3px solid #ff6500;
                    border-radius: 0 4px 4px 0;
                }
                .proposal-footer {
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 10pt;
                }
                .footer-note {
                    color: #666;
                    font-style: italic;
                }
                .footer-note i { margin-right: 6px; color: #ff6500; }
                .footer-summary {
                    display: flex;
                    gap: 20px;
                }
                .summary-item {
                    text-align: center;
                    padding: 10px 20px;
                    background: #fff7ed;
                    border-radius: 8px;
                }
                .summary-label {
                    display: block;
                    font-size: 9pt;
                    color: #666;
                }
                .summary-value {
                    display: block;
                    font-size: 16pt;
                    font-weight: bold;
                    color: #ff6500;
                }
                @media print {
                    body { padding: 20px; }
                    .proposal-section { page-break-inside: avoid; }
                }
            </style>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            ${proposalContent}
        </body>
        </html>
    `);

    printWindow.document.close();

    // Wait for fonts to load then print
    printWindow.onload = function() {
        setTimeout(() => {
            printWindow.print();
        }, 500);
    };

    showToast('PDF export dialog opened', 'success');
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
