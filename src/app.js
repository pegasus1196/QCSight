(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const STORAGE_KEY = 'cabinetsight.runs.v1';
  const API_BASE = window.location.origin + '/api';
  const fileInputs = { photo: $('#photoInput'), drawing: $('#drawingInput'), wire: $('#wireInput'), label: $('#labelInput'), checklist: $('#checklistInput') };
  const names = { photo: $('#photoName'), drawing: $('#drawingName'), wire: $('#wireName'), label: $('#labelName'), checklist: $('#checklistName') };
  let currentRun = null, selectedResultId = null, imageUrl = null;

  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const getHistory = () => { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; } };
  const saveHistory = run => { const h = getHistory(); const i = h.findIndex(x => x.run_id === run.run_id); if (i >= 0) h[i] = run; else h.unshift(run); localStorage.setItem(STORAGE_KEY, JSON.stringify(h.slice(0, 30))); };
  const makeId = () => `CS-${new Date().toISOString().slice(2, 10).replaceAll('-', '')}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;

  /* ═══ THEME ═══ */
  function initTheme() {
    try {
      const saved = localStorage.getItem('cabinetsight.theme');
      if (saved) document.documentElement.setAttribute('data-theme', saved);
    } catch {}
  }

  $('#themeToggle').addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    const next = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('cabinetsight.theme', next); } catch {}
    showToast(`Switched to ${next} mode`, 'info');
  });

  /* ═══ TOAST SYSTEM ═══ */
  function showToast(message, type = 'info') {
    const container = $('#toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '&#10003;', error: '&#10007;', warning: '!', info: 'i' };
    toast.innerHTML = `<span class="toast-icon">${icons[type] || 'i'}</span><span class="toast-msg">${esc(message)}</span><button class="toast-close">&times;</button>`;
    toast.querySelector('.toast-close').addEventListener('click', () => dismissToast(toast));
    container.appendChild(toast);
    setTimeout(() => dismissToast(toast), 4500);
  }

  function dismissToast(toast) {
    if (!toast.parentNode) return;
    toast.classList.add('removing');
    setTimeout(() => toast.remove(), 300);
  }

  /* ═══ NAVBAR ═══ */
  const navbar = $('#navbar');
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });

  $('#hamburger').addEventListener('click', () => {
    $('#navLinks').classList.toggle('open');
  });

  $$('.nav-link').forEach(link => {
    link.addEventListener('click', () => $('#navLinks').classList.remove('open'));
  });

  const sectionObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        $$('.nav-link').forEach(l => l.classList.toggle('active', l.getAttribute('href') === `#${entry.target.id}`));
      }
    });
  }, { threshold: 0.2, rootMargin: '-80px 0px -50% 0px' });
  ['features', 'workspace', 'technology', 'process', 'architecture'].forEach(id => {
    const el = document.getElementById(id);
    if (el) sectionObserver.observe(el);
  });

  /* ═══ STAT COUNTERS ═══ */
  const statsObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      $$('.stat-card', entry.target).forEach(card => {
        const target = parseInt(card.dataset.target, 10);
        const suffix = card.dataset.suffix ?? '';
        const numEl = card.querySelector('.stat-number');
        if (numEl.dataset.animated) return;
        numEl.dataset.animated = '1';
        let current = 0;
        const step = Math.max(1, Math.ceil(target / 50));
        const timer = setInterval(() => {
          current = Math.min(current + step, target);
          numEl.textContent = current + suffix;
          if (current >= target) clearInterval(timer);
        }, 30);
      });
      statsObserver.unobserve(entry.target);
    });
  }, { threshold: 0.4 });
  const statsEl = $('#stats');
  if (statsEl) statsObserver.observe(statsEl);

  /* ═══ WORKSPACE TABS ═══ */
  $$('.ws-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.ws-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      $('#inspectTab').classList.toggle('hidden', target !== 'inspect');
      $('#historyTab').classList.toggle('hidden', target !== 'history');
      if (target === 'history') renderHistory();
    });
  });

  /* ═══ FILE UPLOADS ═══ */
  Object.entries(fileInputs).forEach(([key, input]) => {
    input.addEventListener('change', () => {
      const f = input.files[0];
      if (!f) return;
      const valid = { photo: /\.(jpe?g|png)$/i, drawing: /\.pdf$/i, wire: /\.(xlsx?|csv)$/i, label: /\.(xlsx?|csv)$/i, checklist: /\.(xlsx?|csv)$/i }[key];
      if (!valid.test(f.name)) {
        input.value = '';
        showToast(`Unsupported file type for ${key}. Choose an accepted format.`, 'error');
        return;
      }
      names[key].textContent = f.name;
      names[key].classList.add('selected');
      if (key === 'photo') setPhoto(f);
      updateReady();
      showToast(`${f.name} loaded`, 'success');
    });
  });

  function setPhoto(file) {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    imageUrl = file ? URL.createObjectURL(file) : null;
    const img = $('#cabinetPreview');
    img.src = imageUrl || 'assets/cabinet-demo.png';
    img.alt = file ? 'Uploaded cabinet photo' : 'Cabinet QC demo';
  }

  function updateReady() {
    const ready = fileInputs.photo.files[0] != null;
    $('#runButton').disabled = !ready;
  }

  /* ═══ DEMO BUTTON ═══ */
  $('#demoButton').addEventListener('click', () => {
    Object.keys(fileInputs).forEach(k => {
      fileInputs[k].value = '';
      names[k].textContent = k === 'checklist' ? 'No template selected' : `demo_${k}.${k === 'photo' ? 'jpg' : k === 'drawing' ? 'pdf' : 'xlsx'}`;
      names[k].classList.add('selected');
    });
    $('#runButton').disabled = false;
    setPhoto(null);
    showToast('Demo references loaded. Run the inspection to view sample results.', 'info');
  });

  const heroDemoBtn = $('#heroDemoBtn');
  if (heroDemoBtn) {
    heroDemoBtn.addEventListener('click', () => {
      document.getElementById('workspace').scrollIntoView({ behavior: 'smooth' });
      setTimeout(() => $('#demoButton').click(), 700);
    });
  }

  /* ═══ CHECKS & CONFIDENCE ═══ */
  $('#resetChecks').addEventListener('click', () => {
    $$('[data-check]').forEach(c => c.checked = c.dataset.check !== 'colour');
    showToast('Default checks restored', 'info');
  });

  $('#confidence').addEventListener('input', e => {
    $('#confValue').textContent = `${e.target.value}%`;
  });

  function selectedChecks() {
    return $$('[data-check]:checked').map(c => c.dataset.check);
  }

  /* ═══ PIPELINE STATUS ═══ */
  function updatePipeline(statuses) {
    const items = $$('#pipelineList .pipeline-item');
    statuses.forEach((s, i) => {
      if (!items[i]) return;
      const dot = items[i].querySelector('.pip-dot');
      const label = items[i].querySelector('.pip-status');
      dot.className = `pip-dot ${s.state}`;
      label.textContent = s.label;
    });
  }

  function resetPipeline() {
    updatePipeline([
      { state: 'ready', label: 'Ready' },
      { state: 'ready', label: 'Ready' },
      { state: 'ready', label: 'Ready' },
      { state: 'ready', label: 'Ready' }
    ]);
  }

  /* ═══ DEMO DATA ═══ */
  const demoChecks = {
    presence: { label: 'Device presence', rows: [
      { name: 'Power supply · PS12', expected: 'Installed', found: 'Missing', status: 'FAIL', confidence: .97, box: [42, 8, 19, 23], detail: 'The drawing calls for power supply PS12. The device is missing from the cabinet.', suggestion: 'Install power supply unit PS12 in mounting position A1 as indicated on the GA drawing. Ensure DIN rail clip is secure and verify 24VDC input/output wiring matches the wire list before powering on.' },
      { name: 'Breakers · CB41, CB42', expected: 'Present', found: 'Present', status: 'PASS', confidence: .96 },
      { name: 'Breaker order', expected: 'CB41-42-43-44', found: 'CB43 ↔ CB44 swapped', status: 'FAIL', confidence: .92, box: [68, 7, 20, 24], detail: 'Expected breakers in order CB41–CB44. Photo shows CB43 and CB44 swapped.', suggestion: 'Swap circuit breakers CB43 and CB44 to restore the correct sequence CB41 → CB42 → CB43 → CB44 (left to right). De-energise the panel before repositioning. Re-land wires according to the wire list after swapping.' },
      { name: 'Earth bar · PE', expected: 'Present', found: 'Present', status: 'PASS', confidence: .95 }
    ] },
    labels: { label: 'Device labels', rows: [
      { name: 'Power supply label', expected: 'PS11', found: 'PS11', status: 'PASS', confidence: .98 },
      { name: 'Baseplate label', expected: '1CBP03', found: 'No label', status: 'FAIL', confidence: .90, box: [34, 48, 28, 20], detail: 'Expected label 1CBP03. No readable label is present.', suggestion: 'Print and attach device label "1CBP03" to the baseplate at the marked position. Use an approved label printer (e.g. Brady BMP21) with white-on-black tape to ensure OCR readability during re-check.' }
    ] },
    ferrules: { label: 'Wire ferrules', rows: [
      { name: 'Ferrule on X3 wire', expected: 'Ferrule fitted', found: 'No ferrule', status: 'FAIL', confidence: .91, box: [72, 45, 22, 22], detail: 'The X3 wire end should have a printed ferrule. None visible.', suggestion: 'Strip 8mm of insulation from wire X3 and crimp a printed ferrule sleeve marked "X3" using the appropriate ferrule crimping tool. Ensure the ferrule marking faces outward for OCR visibility during re-check.' }
    ] },
    alignment: { label: 'Photo alignment', rows: [
      { name: 'Photo to GA registration', expected: 'Aligned', found: 'Alignment 94%', status: 'PASS', confidence: .94 }
    ] },
    colour: { label: 'Wire colour', rows: [
      { name: '24 VDC positive', expected: 'Red', found: 'Red', status: 'PASS', confidence: .89 },
      { name: 'Neutral', expected: 'Blue', found: 'Blue', status: 'PASS', confidence: .87 }
    ] }
  };

  /* ═══ BACKEND ═══ */
  async function isBackendAvailable() {
    try {
      const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
      return resp.ok;
    } catch { return false; }
  }

  async function runBackendInspection(isDemo) {
    const active = selectedChecks();
    const confidence = Number($('#confidence').value) / 100;
    if (isDemo) {
      const form = new FormData();
      form.append('confidence_threshold', confidence);
      form.append('checks', active.join(','));
      const resp = await fetch(`${API_BASE}/inspect/demo`, { method: 'POST', body: form });
      if (!resp.ok) throw new Error(`Backend error: ${resp.status}`);
      return await resp.json();
    }
    const form = new FormData();
    form.append('photo', fileInputs.photo.files[0]);
    if (fileInputs.drawing.files[0]) form.append('reference', fileInputs.drawing.files[0]);
    if (fileInputs.wire.files[0]) form.append('wire_list', fileInputs.wire.files[0]);
    if (fileInputs.label.files[0]) form.append('label_list', fileInputs.label.files[0]);
    form.append('project_name', $('#projectName').value.trim() || 'Untitled project');
    form.append('checks', active.join(','));
    form.append('confidence_threshold', confidence);
    const resp = await fetch(`${API_BASE}/inspect`, { method: 'POST', body: form });
    if (!resp.ok) throw new Error(`Backend error: ${resp.status}`);
    return await resp.json();
  }

  function buildDemoRun(recheck) {
    const active = selectedChecks();
    let rows = [];
    active.forEach(key => {
      if (demoChecks[key]) rows.push(...demoChecks[key].rows.map((r, i) => ({ ...r, id: `${key}-${i}`, check: demoChecks[key].label })));
    });
    if (recheck && currentRun) {
      rows = currentRun.results.map(r => {
        if (r.status === 'PASS' || r.status === 'CLOSED') return { ...r };
        if (r.status === 'FAIL' && !r.fixed) {
          return { ...r, status: r.id === 'presence-0' ? 'CLOSED' : 'FAIL', fixed: r.id === 'presence-0', found: r.id === 'presence-0' ? 'PS12 installed at A1' : 'No change detected' };
        }
        return { ...r };
      });
    }
    return {
      run_id: makeId(), timestamp: new Date().toISOString(),
      project: $('#projectName').value.trim() || 'Untitled project',
      photo_file: fileInputs.photo.files[0]?.name || 'demo_photo.jpg', photo_hash: 'local-prototype',
      drawing: fileInputs.drawing.files[0]?.name || 'demo_drawing.pdf',
      wire_list: fileInputs.wire.files[0]?.name || 'demo_wire_list.xlsx',
      label_list: fileInputs.label.files[0]?.name || 'demo_label_list.xlsx',
      checks_run: active, confidence_threshold: Number($('#confidence').value) / 100,
      results: rows, parent_run: recheck ? currentRun.run_id : null, mode: 'Illustrative demo'
    };
  }

  /* ═══ RUN INSPECTION ═══ */
  async function newRun(recheck = false) {
    const btn = $('#runButton');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing…';

    updatePipeline([
      { state: 'running', label: 'Running…' },
      { state: 'running', label: 'Running…' },
      { state: 'running', label: 'Running…' },
      { state: 'running', label: 'Running…' }
    ]);

    const startTime = performance.now();
    let run;

    try {
      const backendUp = await isBackendAvailable();
      if (backendUp && !recheck) {
        const isDemo = !fileInputs.photo.files[0];
        const apiResult = await runBackendInspection(isDemo);
        run = {
          ...apiResult,
          parent_run: recheck ? currentRun?.run_id : null,
          photo_hash: 'cv-analysis',
          drawing: fileInputs.drawing.files[0]?.name || apiResult.drawing || 'N/A',
          wire_list: fileInputs.wire.files[0]?.name || 'N/A',
          label_list: fileInputs.label.files[0]?.name || 'N/A',
          mode: 'CV Analysis',
        };
        $('#resultsBadge').textContent = 'CV RESULTS';
        $('#resultsBadge').className = 'results-badge cv';
        showToast('CV analysis complete — ORB/SIFT + OCR pipeline', 'success');
      } else {
        run = buildDemoRun(recheck);
        $('#resultsBadge').textContent = 'DEMO RESULTS';
        $('#resultsBadge').className = 'results-badge demo';
        showToast(recheck ? 'Re-check complete. Fixed items marked CLOSED.' : 'Inspection complete — demo results (backend offline)', 'warning');
      }
    } catch (err) {
      console.error('Backend error, fallback to demo:', err);
      run = buildDemoRun(recheck);
      $('#resultsBadge').textContent = 'DEMO RESULTS';
      $('#resultsBadge').className = 'results-badge demo';
      showToast('Backend unavailable — showing demo results', 'warning');
    }

    const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
    updatePipeline([
      { state: 'done', label: 'Done' },
      { state: 'done', label: 'Done' },
      { state: 'done', label: 'Done' },
      { state: 'done', label: 'Done' }
    ]);

    btn.disabled = false;
    btn.innerHTML = originalHTML;
    currentRun = run;
    saveHistory(run);
    renderRun(run);
    $('#resultsArea').classList.remove('hidden');
    $('#resultProject').textContent = run.project;
    $('#runMeta').textContent = `Run ID · ${run.run_id}   /   ${new Date(run.timestamp).toLocaleString()}`;

    const isCV = run.mode === 'CV Analysis';
    const details = $('#analysisDetails');
    if (isCV && run.analysis) {
      details.classList.remove('hidden');
      $('#orbCount').textContent = run.analysis.orb_keypoints ?? '—';
      $('#siftCount').textContent = run.analysis.sift_features ?? '—';
      $('#ocrCount').textContent = run.analysis.ocr_texts ?? '—';
    } else if (!isCV) {
      details.classList.remove('hidden');
      $('#orbCount').textContent = '1,308';
      $('#siftCount').textContent = '368';
      $('#ocrCount').textContent = '7';
    }
    $('#procTime').textContent = `${elapsed}s`;

    $('#historyCompare').classList.toggle('hidden', !recheck);
    if (recheck) renderComparison(previousForCompare(run));
    if (run.results.length) selectResult(run.results.find(r => r.status === 'FAIL') || run.results[0]);

    setTimeout(() => {
      $('#resultsArea').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 200);
  }

  function previousForCompare(run) {
    return getHistory().find(x => x.run_id === run.parent_run);
  }

  $('#runButton').addEventListener('click', () => newRun(false));
  $('#recheckButton').addEventListener('click', () => newRun(true));

  /* ═══ RENDER RESULTS ═══ */
  function renderRun(run) {
    const counts = { PASS: 0, FAIL: 0, UNREADABLE: 0, CLOSED: 0, NOT_AUTOMATED: 0 };
    run.results.forEach(r => counts[r.status] = (counts[r.status] || 0) + 1);
    $('#passCount').textContent = counts.PASS + counts.CLOSED;
    $('#failCount').textContent = counts.FAIL;
    $('#unreadCount').textContent = counts.UNREADABLE;
    $('#totalCount').textContent = run.results.length;
    renderTable();
    renderMarkers();
  }

  function renderTable() {
    if (!currentRun) return;
    const filter = $('#statusFilter').value;
    const items = currentRun.results.filter(r => filter === 'all' || r.status === filter);
    $('#resultsBody').innerHTML = items.map(r =>
      `<tr data-id="${esc(r.id)}" class="${selectedResultId === r.id ? 'selected-row' : ''}">
        <td class="item-name">${esc(r.name)}<span class="secondary-text">${esc(r.check)}</span></td>
        <td>${esc(r.expected)}</td>
        <td>${esc(r.found)}</td>
        <td><span class="status ${esc(r.status)}">${esc(r.status)}</span></td>
      </tr>`
    ).join('') || '<tr><td colspan="4" style="padding:24px;color:var(--text-3)">No items match this filter.</td></tr>';
    $('#visibleCount').textContent = `Showing ${items.length} of ${currentRun.results.length}`;
    $$('#resultsBody tr[data-id]').forEach(row =>
      row.addEventListener('click', () => selectResult(currentRun.results.find(x => x.id === row.dataset.id)))
    );
  }

  $('#statusFilter').addEventListener('change', renderTable);
  $('#showAll').addEventListener('click', () => { $('#statusFilter').value = 'all'; renderTable(); });

  function renderMarkers() {
    const root = $('#photoMarkers');
    root.innerHTML = '';
    if (!currentRun) return;
    const frame = $('#photoFrame'), img = $('#cabinetPreview'), fr = frame.getBoundingClientRect();
    const iw = img.naturalWidth || 1, ih = img.naturalHeight || 1;
    const scale = Math.min(fr.width / iw, fr.height / ih);
    const rw = iw * scale, rh = ih * scale, ox = (fr.width - rw) / 2, oy = (fr.height - rh) / 2;
    currentRun.results.filter(r => r.box && ['FAIL', 'UNREADABLE'].includes(r.status)).forEach((r, i) => {
      const m = document.createElement('button');
      m.className = `photo-marker ${r.status === 'UNREADABLE' ? 'unread' : ''} ${selectedResultId === r.id ? 'active' : ''}`;
      m.title = r.name;
      m.dataset.number = String(i + 1);
      const [x, y, w, h] = r.box;
      m.style.cssText = `left:${(ox + rw * x / 100) / fr.width * 100}%;top:${(oy + rh * y / 100) / fr.height * 100}%;width:${rw * w / 100 / fr.width * 100}%;height:${rh * h / 100 / fr.height * 100}%`;
      m.addEventListener('click', () => selectResult(r));
      root.appendChild(m);
    });
  }

  function selectResult(r) {
    if (!r) return;
    selectedResultId = r.id;
    renderTable();
    renderMarkers();
    $('#evidenceLabel').textContent = `· ${r.name}`;
    const icon = r.status === 'FAIL'
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
      : r.status === 'UNREADABLE'
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
    $('#evidenceDetail').innerHTML = `${icon}<div><strong>${esc(r.name)} <span class="status ${esc(r.status)}">${esc(r.status)}</span></strong><small>Expected: ${esc(r.expected)}<br>Found: ${esc(r.found)}${r.detail ? `<br>${esc(r.detail)}` : ''}<br>Confidence: ${Math.round((r.confidence || 0) * 100)}%</small></div>`;

    const suggBox = $('#aiSuggestion');
    const suggText = $('#aiSuggestionText');
    if (r.suggestion && (r.status === 'FAIL' || r.status === 'UNREADABLE')) {
      suggText.textContent = r.suggestion;
      suggBox.classList.remove('hidden');
    } else {
      suggBox.classList.add('hidden');
    }
  }

  function renderComparison(previous) {
    if (!previous) return;
    const closed = currentRun.results.filter(x => x.status === 'CLOSED').length;
    const still = currentRun.results.filter(x => x.status === 'FAIL').length;
    const passed = currentRun.results.filter(x => x.status === 'PASS').length;
    $('#compareSummary').textContent = `${previous.run_id} → ${currentRun.run_id} · PASS items carried forward.`;
    $('#compareStats').innerHTML = `<div class="compare-chips"><span class="compare-chip closed">${closed} closed</span><span class="compare-chip">${still} still open</span><span class="compare-chip">${passed} passed</span></div>`;
  }

  /* ═══ EXPORT ═══ */
  $('#exportButton').addEventListener('click', () => {
    if (!currentRun) return;
    const csv = [
      ['Run ID', 'Project', 'Check', 'Item', 'Expected', 'Found', 'Status', 'Confidence'],
      ...currentRun.results.map(r => [currentRun.run_id, currentRun.project, r.check, r.name, r.expected, r.found, r.status, `${Math.round(r.confidence * 100)}%`])
    ].map(row => row.map(v => `"${String(v ?? '').replaceAll('"', '""')}"`).join(',')).join('\r\n');

    download(`${currentRun.run_id}-checklist.csv`, new Blob(['﻿', csv], { type: 'text/csv;charset=utf-8' }));

    const w = window.open('', '_blank');
    if (w) { w.document.write(reportHtml(currentRun)); w.document.close(); setTimeout(() => w.print(), 500); }
    showToast('Checklist CSV downloaded. Use Print to save as PDF.', 'success');
  });

  function download(name, blob) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function reportHtml(run) {
    const modeLabel = run.mode === 'CV Analysis' ? 'CV PIPELINE RESULTS' : 'ILLUSTRATIVE PROTOTYPE RESULTS';
    return `<!doctype html><html><head><title>CabinetSight Report</title><style>body{font:13px 'Space Grotesk',Arial,sans-serif;color:#0F172A;margin:38px;background:#fff}h1{font-size:22px;margin-bottom:6px}.badge{color:#0284C7;background:#E0F2FE;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:600}.meta{line-height:1.8;margin:16px 0;font-size:12px;color:#475569}table{width:100%;border-collapse:collapse;margin-top:18px}th,td{text-align:left;padding:10px;border-bottom:1px solid #E2E8F0;font-size:11px}th{background:#F1F5F9;font-weight:700;color:#64748B;font-size:9px;letter-spacing:0.5px}footer{margin-top:28px;color:#94A3B8;font-size:9px}@media print{body{margin:18mm}}</style></head><body><div style="color:#0284C7;font-size:10px;letter-spacing:1.5px;font-weight:600">CABINETSIGHT · PROJECT EAGLE EYE</div><h1>Quality Control Inspection Report</h1><span class="badge">${esc(modeLabel)}</span><div class="meta"><b>Project:</b> ${esc(run.project)}<br><b>Run:</b> ${esc(run.run_id)}<br><b>Time:</b> ${esc(new Date(run.timestamp).toLocaleString())}<br><b>Photo:</b> ${esc(run.photo_file)} · <b>Drawing:</b> ${esc(run.drawing || 'N/A')}<br><b>Checks:</b> ${esc(run.checks_run.join(', '))}<br><b>Mode:</b> ${esc(run.mode)}</div><table><thead><tr><th>ITEM</th><th>EXPECTED</th><th>FOUND</th><th>RESULT</th><th>CONFIDENCE</th></tr></thead><tbody>${run.results.map(r => `<tr><td><b>${esc(r.name)}</b></td><td>${esc(r.expected)}</td><td>${esc(r.found)}</td><td><b>${esc(r.status)}</b></td><td>${Math.round(r.confidence * 100)}%</td></tr>`).join('')}</tbody></table><footer>${run.mode === 'CV Analysis' ? 'Results from ORB/SIFT feature matching + OCR pipeline.' : 'Prototype demonstration only.'} All files remain local.</footer></body></html>`;
  }

  /* ═══ HISTORY ═══ */
  function renderHistory() {
    const list = getHistory();
    const root = $('#historyList');
    if (!list.length) {
      root.innerHTML = `<div class="history-empty"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg><br><strong>No saved runs yet</strong><br>Completed inspections will appear here.</div>`;
      return;
    }
    root.innerHTML = list.map(r => {
      const count = s => r.results.filter(x => x.status === s).length;
      const icon = r.mode === 'CV Analysis'
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
      return `<div class="history-card"><div class="history-mark">${icon}</div><div class="history-info"><strong>${esc(r.project)}</strong><small>${esc(r.run_id)} · ${new Date(r.timestamp).toLocaleString()}${r.parent_run ? ' · Re-check' : ''} · ${esc(r.mode || 'Demo')}</small></div><div class="history-counts"><span>${count('PASS')} pass</span><span class="hf">${count('FAIL')} fail</span><span>${count('UNREADABLE')} unread</span></div><button class="history-open" data-run="${esc(r.run_id)}">View →</button></div>`;
    }).join('');

    $$('.history-open').forEach(b => b.addEventListener('click', () => {
      const r = getHistory().find(x => x.run_id === b.dataset.run);
      if (!r) return;
      currentRun = r;
      $$('.ws-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === 'inspect'));
      $('#inspectTab').classList.remove('hidden');
      $('#historyTab').classList.add('hidden');
      $('#resultsArea').classList.remove('hidden');
      $('#resultProject').textContent = r.project;
      $('#runMeta').textContent = `Run ID · ${r.run_id}   /   ${new Date(r.timestamp).toLocaleString()}`;
      const badge = $('#resultsBadge');
      if (r.mode === 'CV Analysis') { badge.textContent = 'CV RESULTS'; badge.className = 'results-badge cv'; }
      else { badge.textContent = 'DEMO RESULTS'; badge.className = 'results-badge demo'; }
      renderRun(r);
      $('#historyCompare').classList.toggle('hidden', !r.parent_run);
      if (r.parent_run) renderComparison(getHistory().find(x => x.run_id === r.parent_run));
      $('#resultsArea').scrollIntoView({ behavior: 'smooth' });
    }));
  }

  /* ═══ ZOOM ═══ */
  $('#zoomButton').addEventListener('click', () => {
    $('#zoomContent').innerHTML = `<img src="${imageUrl || 'assets/cabinet-demo.png'}" alt="Cabinet photo">`;
    $('#zoomModal').classList.remove('hidden');
  });
  $('#closeZoom').addEventListener('click', () => $('#zoomModal').classList.add('hidden'));
  $('#zoomModal').addEventListener('click', e => {
    if (e.target === $('#zoomModal')) $('#zoomModal').classList.add('hidden');
  });

  /* ═══ FEATURE DETAIL MODALS ═══ */
  const FEATURES = {
    presence: {
      title: 'Device Presence',
      tag: 'ORB + SIFT',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
      desc: 'Verifies that every component listed in the GA drawing physically exists in the built cabinet. Uses dual keypoint descriptor matching — ORB for speed, SIFT for sub-pixel accuracy — with brute-force matching and Lowe\'s ratio test to eliminate false positives.',
      stats: [
        { val: '96%', label: 'ACCURACY', cls: 'high' },
        { val: '~1300', label: 'ORB KEYPOINTS', cls: 'mid' },
        { val: '0.75', label: 'RATIO TEST', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Load', detail: 'Read photo + GA' },
        { num: '02', name: 'ORB Extract', detail: '1500 keypoints' },
        { num: '03', name: 'BFMatcher', detail: 'Hamming distance' },
        { num: '04', name: 'SIFT Refine', detail: '128-D descriptors' },
        { num: '05', name: 'Verdict', detail: 'Match threshold' }
      ],
      model: [
        { key: 'ALGORITHM', val: 'ORB (Oriented FAST + Rotated BRIEF)' },
        { key: 'REFINER', val: 'SIFT (Scale-Invariant Feature Transform)' },
        { key: 'MATCHER', val: 'BFMatcher with L2 norm + Lowe\'s ratio' },
        { key: 'LIBRARY', val: 'OpenCV 5.0 (cv2)' }
      ],
      params: [
        { name: 'nfeatures', val: '1500' },
        { name: 'ratio_test', val: '0.75' },
        { name: 'min_matches', val: '15' },
        { name: 'scale_factor', val: '1.2' }
      ]
    },
    labels: {
      title: 'Label Verification',
      tag: 'EasyOCR + RapidFuzz',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7V4h16v3M9 20h6M12 4v16"/></svg>',
      desc: 'Reads printed device labels from the cabinet photo using a CRAFT text detector + CRNN recogniser (EasyOCR), then fuzzy-matches each OCR result against the expected label list using RapidFuzz. Partial matches (40-80%) are flagged UNREADABLE; confirmed matches (>80%) pass.',
      stats: [
        { val: '80%', label: 'MATCH THRESHOLD', cls: 'high' },
        { val: 'CRAFT', label: 'TEXT DETECTOR', cls: 'mid' },
        { val: 'CRNN', label: 'RECOGNISER', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'CLAHE', detail: 'Contrast enhance' },
        { num: '02', name: 'CRAFT', detail: 'Detect text regions' },
        { num: '03', name: 'CRNN', detail: 'Recognise text' },
        { num: '04', name: 'RapidFuzz', detail: 'Fuzzy match 80%' },
        { num: '05', name: 'Verdict', detail: 'PASS / UNREADABLE / FAIL' }
      ],
      model: [
        { key: 'OCR ENGINE', val: 'EasyOCR (CRAFT + CRNN)' },
        { key: 'FALLBACK', val: 'Tesseract OCR (pytesseract)' },
        { key: 'MATCHER', val: 'RapidFuzz (token_sort_ratio)' },
        { key: 'PRE-PROCESS', val: 'CLAHE + grayscale + bilateral filter' }
      ],
      params: [
        { name: 'fuzzy_threshold', val: '80%' },
        { name: 'partial_range', val: '40-80%' },
        { name: 'clip_limit', val: '2.0' },
        { name: 'min_text_len', val: '2 chars' }
      ]
    },
    ferrules: {
      title: 'Wire Ferrules',
      tag: 'ROI + OCR',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
      desc: 'Detects ferrule sleeve markings on wire termination points. Isolates terminal block regions using contour detection, applies targeted OCR on each region of interest, and validates the read marking against the wire list\'s ferrule IDs.',
      stats: [
        { val: '91%', label: 'DETECTION RATE', cls: 'high' },
        { val: 'ROI', label: 'EXTRACTION', cls: 'mid' },
        { val: '80%', label: 'MATCH SCORE', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Locate', detail: 'Terminal block ROI' },
        { num: '02', name: 'Segment', detail: 'Contour isolation' },
        { num: '03', name: 'OCR', detail: 'Read ferrule text' },
        { num: '04', name: 'Match', detail: 'Fuzzy vs wire list' },
        { num: '05', name: 'Verdict', detail: 'Present / Missing' }
      ],
      model: [
        { key: 'REGION DETECT', val: 'Contour-based ROI extraction' },
        { key: 'OCR ENGINE', val: 'EasyOCR (targeted ROI crop)' },
        { key: 'VALIDATION', val: 'RapidFuzz against wire list IDs' },
        { key: 'PRE-PROCESS', val: 'Adaptive threshold + morphology' }
      ],
      params: [
        { name: 'roi_padding', val: '10px' },
        { name: 'min_area', val: '200px²' },
        { name: 'match_threshold', val: '80%' },
        { name: 'max_candidates', val: '50' }
      ]
    },
    alignment: {
      title: 'Photo Alignment',
      tag: 'Homography + RANSAC',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18"/></svg>',
      desc: 'Registers the cabinet photo to the GA drawing coordinate frame using feature-based homography. Extracts ORB/SIFT keypoints from both images, computes a 3×3 perspective transform via RANSAC, and scores alignment quality using Structural Similarity (SSIM).',
      stats: [
        { val: '94%', label: 'SSIM SCORE', cls: 'high' },
        { val: '3×3', label: 'HOMOGRAPHY', cls: 'mid' },
        { val: 'RANSAC', label: 'OUTLIER FILTER', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Keypoints', detail: 'ORB + SIFT extract' },
        { num: '02', name: 'Match', detail: 'BFMatcher L2/Ham' },
        { num: '03', name: 'RANSAC', detail: 'Filter outliers' },
        { num: '04', name: 'Warp', detail: '3×3 homography' },
        { num: '05', name: 'SSIM', detail: 'Similarity score' }
      ],
      model: [
        { key: 'TRANSFORM', val: 'Perspective homography (3×3 matrix)' },
        { key: 'INLIER FILTER', val: 'RANSAC (5.0 reproj threshold)' },
        { key: 'QUALITY METRIC', val: 'SSIM (structural similarity)' },
        { key: 'LIBRARY', val: 'OpenCV warpPerspective + skimage SSIM' }
      ],
      params: [
        { name: 'ransac_thresh', val: '5.0' },
        { name: 'min_inliers', val: '10' },
        { name: 'ssim_window', val: '7×7' },
        { name: 'warp_mode', val: 'INTER_LINEAR' }
      ]
    },
    colour: {
      title: 'Wire Colour',
      tag: 'K-Means + HSV',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="13.5" cy="6.5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M15.5 8.5L17 14.5"/><path d="M8.5 12.5L15.5 17"/></svg>',
      desc: 'Detects wire regions using edge detection and saturation-based masking, then identifies each wire\'s colour via HSV range matching (primary) and K-means clustering (fallback). Validates against IEC 60446 and the uploaded wire colour list.',
      stats: [
        { val: '89%', label: 'COLOUR ACCURACY', cls: 'high' },
        { val: 'HSV', label: 'PRIMARY METHOD', cls: 'mid' },
        { val: '9', label: 'COLOUR CLASSES', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Detect', detail: 'Wire region mask' },
        { num: '02', name: 'HSV Check', detail: 'Range-based match' },
        { num: '03', name: 'K-Means', detail: 'Fallback clustering' },
        { num: '04', name: 'Map', detail: 'Nearest named colour' },
        { num: '05', name: 'Validate', detail: 'vs wire list' }
      ],
      model: [
        { key: 'PRIMARY', val: 'HSV inRange mask (per-colour bounds)' },
        { key: 'FALLBACK', val: 'K-Means clustering (k=3) on BGR' },
        { key: 'COLOURS', val: 'Red, Blue, Green, Yellow, Black, White, Brown, Orange, Grey' },
        { key: 'STANDARD', val: 'IEC 60446 wire colour coding' }
      ],
      params: [
        { name: 'k_clusters', val: '3' },
        { name: 'hsv_ratio_min', val: '0.05' },
        { name: 'min_wire_h', val: '30px' },
        { name: 'confidence_cap', val: '0.95' }
      ]
    },
    yolo: {
      title: 'YOLO Detection',
      tag: 'YOLOv11 + 45 Classes',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
      desc: 'Real-time object detection using YOLOv11 trained on the LibreYOLO/circuit-elements dataset. Identifies 45 classes of electrical components (breakers, relays, PLCs, contactors, etc.) with bounding box localisation and per-class confidence scores.',
      stats: [
        { val: '772', label: 'TRAINING IMAGES', cls: 'high' },
        { val: '45', label: 'COMPONENT CLASSES', cls: 'mid' },
        { val: 'v11', label: 'YOLO VERSION', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Resize', detail: '640×640 input' },
        { num: '02', name: 'Backbone', detail: 'CSPDarknet' },
        { num: '03', name: 'Neck', detail: 'PANet FPN' },
        { num: '04', name: 'Head', detail: 'Decoupled detect' },
        { num: '05', name: 'NMS', detail: 'Filter overlaps' }
      ],
      model: [
        { key: 'ARCHITECTURE', val: 'YOLOv11n (nano variant)' },
        { key: 'DATASET', val: 'LibreYOLO/circuit-elements (CC BY 4.0)' },
        { key: 'IMAGES', val: '772 annotated (YOLO format)' },
        { key: 'FRAMEWORK', val: 'Ultralytics (torch backend)' }
      ],
      params: [
        { name: 'input_size', val: '640×640' },
        { name: 'conf_threshold', val: '0.25' },
        { name: 'iou_threshold', val: '0.45' },
        { name: 'epochs', val: '50' }
      ]
    }
  };

  function openFeatureModal(key) {
    const f = FEATURES[key];
    if (!f) return;
    showDetailModal(f);
  }

  function showDetailModal(data) {
    const modal = $('#featureModal');
    $('#fmIcon').innerHTML = data.icon;
    $('#fmTitle').textContent = data.title;
    $('#fmTag').textContent = data.tag;
    $('#fmDesc').textContent = data.desc;
    $('#fmStats').innerHTML = data.stats.map(s =>
      `<div class="fm-stat"><span class="fm-stat-val ${s.cls}">${s.val}</span><span class="fm-stat-label">${s.label}</span></div>`
    ).join('');
    $('#fmPipeline').innerHTML = data.pipeline.map((p, i) =>
      (i > 0 ? '<span class="fm-arrow">→</span>' : '') +
      `<div class="fm-step"><span class="fm-step-num">${p.num}</span><span class="fm-step-name">${p.name}</span><span class="fm-step-detail">${p.detail}</span></div>`
    ).join('');
    $('#fmModel').innerHTML = data.model.map(m =>
      `<div class="fm-detail-row"><span class="fm-detail-key">${m.key}</span><span class="fm-detail-val">${m.val}</span></div>`
    ).join('');
    $('#fmParams').innerHTML = data.params.map(p =>
      `<div class="fm-param"><span class="fm-param-name">${p.name}</span><span class="fm-param-val">${p.val}</span></div>`
    ).join('');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeFeatureModal() {
    $('#featureModal').classList.add('hidden');
    document.body.style.overflow = '';
  }

  $$('.feature-card[data-feature]').forEach(card => {
    card.addEventListener('click', () => openFeatureModal(card.dataset.feature));
  });
  $('#fmClose').addEventListener('click', closeFeatureModal);
  $('#featureModal').addEventListener('click', e => {
    if (e.target.classList.contains('fm-backdrop')) closeFeatureModal();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !$('#featureModal').classList.contains('hidden')) closeFeatureModal();
  });

  /* ═══ TECH CARD MODALS ═══ */
  const TECH_DATA = {
    orb_sift: {
      title: 'ORB / SIFT',
      tag: 'Feature Detection',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4"/></svg>',
      desc: 'ORB (Oriented FAST and Rotated BRIEF) provides real-time binary keypoint descriptors at ~1500 features per frame. SIFT (Scale-Invariant Feature Transform) adds 128-dimensional floating-point descriptors for sub-pixel accuracy when ORB alone is insufficient. Together they form a robust dual-descriptor pipeline for device presence verification.',
      stats: [
        { val: '~1500', label: 'KEYPOINTS', cls: 'high' },
        { val: '128-D', label: 'SIFT DESCRIPTOR', cls: 'mid' },
        { val: '256-bit', label: 'ORB DESCRIPTOR', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Grayscale', detail: 'BGR → Gray' },
        { num: '02', name: 'ORB Detect', detail: 'FAST corners + BRIEF' },
        { num: '03', name: 'SIFT Detect', detail: 'DoG + gradient hist' },
        { num: '04', name: 'BFMatcher', detail: 'L2 / Hamming' },
        { num: '05', name: 'Lowe’s Test', detail: 'Ratio = 0.75' }
      ],
      model: [
        { key: 'ORB', val: 'Oriented FAST + Rotated BRIEF (binary, Hamming distance)' },
        { key: 'SIFT', val: 'Scale-space extrema + 128-D HOG descriptor' },
        { key: 'MATCHER', val: 'cv2.BFMatcher with crossCheck / KNN' },
        { key: 'OUTLIER', val: 'Lowe’s ratio test (0.75) + RANSAC homography' }
      ],
      params: [
        { name: 'orb_nfeatures', val: '1500' },
        { name: 'sift_octaves', val: '3' },
        { name: 'ratio_thresh', val: '0.75' },
        { name: 'ransac_reproj', val: '5.0' }
      ]
    },
    easyocr: {
      title: 'EasyOCR',
      tag: 'Optical Character Recognition',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 7V4h16v3M9 20h6M12 4v16"/></svg>',
      desc: 'EasyOCR combines a CRAFT (Character Region Awareness for Text) detector with a CRNN (Convolutional Recurrent Neural Network) recogniser. CLAHE pre-processing equalises contrast on industrial labels. RapidFuzz provides fuzzy string matching with configurable thresholds for partial and full match classification.',
      stats: [
        { val: 'CRAFT', label: 'TEXT DETECTOR', cls: 'high' },
        { val: 'CRNN', label: 'RECOGNISER', cls: 'mid' },
        { val: '80+', label: 'LANGUAGES', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'CLAHE', detail: 'Histogram equalise' },
        { num: '02', name: 'Bilateral', detail: 'Noise reduction' },
        { num: '03', name: 'CRAFT', detail: 'Locate text boxes' },
        { num: '04', name: 'CRNN', detail: 'Sequence-to-text' },
        { num: '05', name: 'RapidFuzz', detail: 'token_sort_ratio' }
      ],
      model: [
        { key: 'DETECTOR', val: 'CRAFT — VGG16 backbone, affinity + region maps' },
        { key: 'RECOGNISER', val: 'CRNN — ResNet + BiLSTM + CTC decoder' },
        { key: 'FALLBACK', val: 'Tesseract 5 via pytesseract (LSTM engine)' },
        { key: 'MATCHING', val: 'RapidFuzz token_sort_ratio, threshold 80%' }
      ],
      params: [
        { name: 'clip_limit', val: '2.0' },
        { name: 'match_thresh', val: '80%' },
        { name: 'partial_range', val: '40–80%' },
        { name: 'languages', val: '[\"en\"]' }
      ]
    },
    yolov11: {
      title: 'YOLOv11',
      tag: 'Object Detection',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
      desc: 'YOLOv11 (You Only Look Once, version 11) is a single-shot real-time object detector. Trained on the LibreYOLO/circuit-elements dataset (772 annotated images, CC BY 4.0 license) covering 45 classes of electrical components found in industrial cabinets — breakers, contactors, relays, PLCs, fuses, terminals, and more.',
      stats: [
        { val: '772', label: 'TRAINING IMAGES', cls: 'high' },
        { val: '45', label: 'CLASSES', cls: 'mid' },
        { val: 'nano', label: 'MODEL VARIANT', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'Resize', detail: '640×640 letterbox' },
        { num: '02', name: 'Backbone', detail: 'CSPDarknet53' },
        { num: '03', name: 'Neck', detail: 'PANet + FPN' },
        { num: '04', name: 'Head', detail: 'Decoupled detect' },
        { num: '05', name: 'NMS', detail: 'IoU 0.45 filter' }
      ],
      model: [
        { key: 'ARCHITECTURE', val: 'YOLOv11n (nano) — CSPDarknet + PANet + decoupled head' },
        { key: 'DATASET', val: 'LibreYOLO/circuit-elements (HuggingFace, CC BY 4.0)' },
        { key: 'CLASSES', val: 'breaker, contactor, relay, PLC, fuse, terminal, transformer…' },
        { key: 'FRAMEWORK', val: 'Ultralytics + PyTorch (CUDA / CPU)' }
      ],
      params: [
        { name: 'input_size', val: '640×640' },
        { name: 'conf_thresh', val: '0.25' },
        { name: 'iou_thresh', val: '0.45' },
        { name: 'epochs', val: '50' }
      ]
    },
    opencv: {
      title: 'OpenCV 5',
      tag: 'Computer Vision Library',
      icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
      desc: 'OpenCV 5 is the backbone of the entire CabinetSight pipeline. It handles image I/O, colour space conversions (BGR → HSV/Gray), perspective warping via homography matrices, contour detection for region isolation, morphological operations, and the CLAHE adaptive histogram equalisation used in OCR pre-processing.',
      stats: [
        { val: '2500+', label: 'ALGORITHMS', cls: 'high' },
        { val: 'v5.0', label: 'VERSION', cls: 'mid' },
        { val: 'C++/Py', label: 'BINDINGS', cls: 'accent' }
      ],
      pipeline: [
        { num: '01', name: 'imread', detail: 'Load + decode' },
        { num: '02', name: 'cvtColor', detail: 'Colour transform' },
        { num: '03', name: 'warpPerspective', detail: 'Homography' },
        { num: '04', name: 'findContours', detail: 'Edge detection' },
        { num: '05', name: 'inRange', detail: 'HSV masking' }
      ],
      model: [
        { key: 'HOMOGRAPHY', val: 'findHomography with RANSAC (perspective 3×3)' },
        { key: 'COLOUR', val: 'cvtColor BGR→HSV + inRange masking' },
        { key: 'MORPHOLOGY', val: 'erode, dilate, morphologyEx (open/close)' },
        { key: 'CONTOURS', val: 'findContours + boundingRect for ROI extraction' }
      ],
      params: [
        { name: 'interpolation', val: 'INTER_LINEAR' },
        { name: 'morph_kernel', val: '5×5' },
        { name: 'canny_low', val: '50' },
        { name: 'canny_high', val: '150' }
      ]
    }
  };

  $$('.tech-card[data-tech]').forEach(card => {
    card.addEventListener('click', () => {
      const data = TECH_DATA[card.dataset.tech];
      if (data) showDetailModal(data);
    });
  });

  /* ═══ SCROLL ANIMATIONS ═══ */
  const scrollReveal = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.15 });

  $$('#processTimeline .process-step, #processTimeline .process-connector').forEach((el, i) => {
    el.style.transitionDelay = `${i * 0.1}s`;
    scrollReveal.observe(el);
  });
  $$('#archDiagram .arch-layer, #archDiagram .arch-flow-arrow').forEach((el, i) => {
    el.style.transitionDelay = `${i * 0.15}s`;
    scrollReveal.observe(el);
  });

  /* ═══ INIT ═══ */
  initTheme();
  updateReady();

  isBackendAvailable();
})();
