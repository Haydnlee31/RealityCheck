(() => {
  'use strict';
  const config = window.REALITYCHECK_CONFIG || {};
  if (config.DEMO_VIDEO_URL) {
    try {
      const url = new URL(config.DEMO_VIDEO_URL);
      if (url.protocol === 'https:') document.querySelectorAll('.video-link').forEach(link => {
        link.href = url.href;
        link.hidden = false;
      });
    } catch { /* An absent or invalid URL keeps the video buttons hidden. */ }
  }

  // Native disclosures preserve the complete architecture without JavaScript.
  document.querySelectorAll('.workflow-step').forEach(step => {
    step.addEventListener('toggle', () => {
      if (!step.open) return;
      document.querySelectorAll('.workflow-step').forEach(other => {
        if (other !== step) other.open = false;
      });
    });
  });

  const scenarioFilter = document.querySelector('.scenario-filter');
  if (scenarioFilter) {
    scenarioFilter.hidden = false;
    scenarioFilter.querySelectorAll('[data-phase]').forEach(button => {
      button.addEventListener('click', () => {
        const phase = button.dataset.phase;
        scenarioFilter.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
        document.querySelectorAll('.before-column').forEach(cell => { cell.hidden = phase === 'after'; });
        document.querySelectorAll('.after-column').forEach(cell => { cell.hidden = phase === 'before'; });
      });
    });
  }

  const bundle = window.RC_EVIDENCE;
  if (bundle?.findings?.length) {
    const explorer = document.querySelector('#evidence-explorer');
    const panel = document.querySelector('#execution-panel');
    let findingId = 'RC-001';
    let phase = 'reproduction';
    const descriptions = {
      'RC-001': 'An invoice identifier must survive ingestion, storage, and lookup unchanged. The accepted counterexample is the synthetic string “053636”.',
      'RC-002': 'A failed batch must leave no newly inserted rows behind. Pre-existing records must remain unchanged.',
      'RC-003': 'Exact replays add no row. Conflicting identities fail clearly. Distinct identities remain distinct, even with equal business values.'
    };

    // Evidence is rendered as text, never interpreted as HTML or executable code.
    const el = (tag, className, text) => {
      const element = document.createElement(tag);
      if (className) element.className = className;
      if (text !== undefined) element.textContent = text;
      return element;
    };
    const metric = (label, value) => {
      const box = el('div');
      box.append(el('span', '', label), el('strong', '', String(value)));
      return box;
    };
    function render() {
      const finding = bundle.findings.find(f => f.id === findingId);
      if (!finding) return;
      const execution = finding.executions[phase];
      if (!execution) return;
      const record = execution.record;
      const results = record.structured_results;
      const passed = record.outcome === 'passed';
      document.querySelectorAll('[data-finding]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.finding === findingId)));
      document.querySelectorAll('[data-execution]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.execution === phase)));
      document.querySelector('#evidence-requirement').textContent = finding.requirement;
      document.querySelector('#evidence-summary').textContent = descriptions[findingId];
      document.querySelector('#acceptance-time').textContent = finding.acceptedAt.replace('T', ' ').replace('+00:00', ' UTC');
      document.querySelector('#evidence-report').href = finding.report;
      document.querySelector('#evidence-json').href = finding.evidence;
      document.querySelector('#evidence-manifest').href = finding.manifest;
      const fragment = document.createDocumentFragment();
      const title = el('div', 'execution-title');
      title.append(el('strong', passed ? 'green' : 'red', `${passed ? '✓' : '×'} ${passed ? 'Passed' : 'Failed'}`), el('span', '', `EXIT ${record.exit_code}`));
      fragment.append(title);
      const metrics = el('div', 'execution-metrics');
      metrics.append(metric('Tests', results.tests), metric('Failures', results.failures), metric('Errors', results.errors), metric('Skipped', results.skipped));
      fragment.append(metrics);
      const tests = el('ul', 'execution-test-list');
      results.cases.forEach(test => {
        const pass = test.status === 'passed';
        const li = el('li');
        li.append(el('span', `result-icon ${pass ? 'green' : 'red'}`, pass ? '✓' : '×'), el('code', '', test.name), el('span', 'sr-only', `: ${test.status}`));
        tests.append(li);
      });
      fragment.append(tests);
      const metadata = el('dl', 'execution-metadata');
      const fields = [
        ['Execution', record.execution_id],
        ['Snapshot', record.application_snapshot],
        ['Manifest', record.protected_manifest?.ok === true ? 'Verified at this execution · no missing or modified files' : 'Not verified'],
        ['Recorded', record.started_at],
        ['Duration', `${record.duration_ms} ms · pytest subprocess only`]
      ];
      fields.forEach(([key, value]) => { metadata.append(el('dt', '', key), el('dd', key === 'Manifest' ? 'green' : '', value)); });
      fragment.append(metadata);
      const actions = el('div', 'execution-actions');
      [['Execution JSON ↗', execution.json], ['JUnit XML ↗', execution.junit], ['Captured output ↗', execution.stdout]].forEach(([label, href]) => {
        const link = el('a', '', label); link.href = href; actions.append(link);
      });
      fragment.append(actions);
      const scope = phase === 'reproduction'
        ? 'Original execution, preserved before repair. Passing guards can coexist with reproduced failures.'
        : 'Recorded verification covers these tests only. It does not certify production readiness.';
      fragment.append(el('p', 'execution-scope', scope));
      panel.replaceChildren(fragment);
    }
    document.querySelector('#source-commit').textContent = bundle.sourceCommit.slice(0, 7);
    document.querySelectorAll('[data-finding]').forEach(button => button.addEventListener('click', () => {
      findingId = button.dataset.finding; render();
    }));
    document.querySelectorAll('[data-execution]').forEach(button => button.addEventListener('click', () => {
      phase = button.dataset.execution; render();
    }));
    document.querySelectorAll('[data-finding-link]').forEach(link => link.addEventListener('click', () => {
      findingId = link.dataset.findingLink; phase = 'reproduction'; render();
    }));
    render();
    explorer.hidden = false;
    document.querySelector('#evidence-fallback').hidden = true;
  }

  if ('IntersectionObserver' in window) {
    const links = Array.from(document.querySelectorAll('nav a[href^="#"]'));
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        links.forEach(link => {
          if (link.hash === `#${entry.target.id}`) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-15% 0px -65% 0px' });
    links.forEach(link => { const section = document.querySelector(link.hash); if (section) observer.observe(section); });
  }
})();
