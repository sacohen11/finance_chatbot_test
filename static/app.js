const form = document.getElementById('assistant-form');
const answerEl = document.getElementById('answer');
const tableWrap = document.getElementById('table-wrap');
const chartEl = document.getElementById('chart');
const csvBtn = document.getElementById('download-csv');
const pngBtn = document.getElementById('download-png');

let currentRows = [];
let hasChart = false;

function renderTable(rows) {
  if (!rows.length) {
    tableWrap.innerHTML = 'No rows returned.';
    return;
  }

  const headers = Object.keys(rows[0]);
  const thead = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows.map(row => `<tr>${headers.map(h => `<td>${row[h]}</td>`).join('')}</tr>`).join('')}</tbody>`;
  tableWrap.innerHTML = `<table>${thead}${tbody}</table>`;
}

function toCsv(rows) {
  if (!rows.length) return '';
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(',')];
  rows.forEach(row => {
    lines.push(headers.map(h => JSON.stringify(row[h] ?? '')).join(','));
  });
  return lines.join('\n');
}

csvBtn.addEventListener('click', () => {
  const csv = toCsv(currentRows);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'assistant_results.csv';
  a.click();
  URL.revokeObjectURL(url);
});

pngBtn.addEventListener('click', async () => {
  if (!hasChart) return;
  const dataUrl = await Plotly.toImage(chartEl, { format: 'png', width: 1000, height: 600 });
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = 'assistant_chart.png';
  a.click();
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = document.getElementById('query').value.trim();

  const response = await fetch('/api/assistant', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });

  const payload = await response.json();

  answerEl.textContent = payload.answer_text || '';
  currentRows = payload.table_data || [];
  renderTable(currentRows);
  csvBtn.disabled = currentRows.length === 0;

  if (payload.chart_spec) {
    await Plotly.newPlot(chartEl, payload.chart_spec.data, payload.chart_spec.layout || {}, { responsive: true, displayModeBar: true });
    hasChart = true;
    pngBtn.disabled = false;
  } else {
    chartEl.innerHTML = 'No chart recommended for this result.';
    hasChart = false;
    pngBtn.disabled = true;
  }
});
