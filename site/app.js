const PALETTE = ["#3b6ef0", "#15b88a", "#d98c15", "#e0528a", "#8a5cf6", "#2fa9c9"];

let trendSnapshot = null;

async function main() {
  const manifest = await fetchJSON("data/manifest.json");
  const latest = manifest.snapshots[manifest.snapshots.length - 1];
  const snapshot = await fetchJSON(latest.data);
  trendSnapshot = snapshot;

  document.getElementById("subtitle").textContent =
    `${latest.title} — source: ${snapshot.source}`;

  if (latest.report) {
    document.getElementById("report-link").innerHTML =
      `Full narrative report: <a href="${latest.report.replace("snapshots/", "../snapshots/")}">${latest.report}</a>`;
  } else {
    document.getElementById("report-link").textContent =
      "Automated snapshot — no narrative report for this run.";
  }
  document.getElementById("methodology").textContent = snapshot.methodology || "";

  setupTrendSection(snapshot);
  renderStats(snapshot);
  renderLevel(snapshot);
  renderCloud(snapshot);
  renderOrEmpty("chart-weekly", snapshot.weekly_postings, () => renderWeekly(snapshot));
  renderOrEmpty("chart-skills", snapshot.skills_pct, () => renderBarPct("chart-skills", snapshot.skills_pct, "skill"));
  renderOrEmpty("chart-resp", snapshot.responsibilities_pct, () => renderBarPct("chart-resp", snapshot.responsibilities_pct, "responsibility"));
}

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`);
  return res.json();
}

function renderOrEmpty(canvasId, data, renderFn) {
  if (!data || data.length === 0) {
    const canvas = document.getElementById(canvasId);
    const note = document.createElement("p");
    note.className = "empty-note";
    note.textContent = "No data in this snapshot yet.";
    canvas.replaceWith(note);
    return;
  }
  renderFn();
}

// ---------- Market trend section ----------

let trendLevelChart = null;
let trendMomChart = null;

function setupTrendSection(s) {
  const section = document.getElementById("trend-section");
  const trend = s.monthly_trend;
  if (!trend || !trend.metrics || trend.metrics.length === 0) {
    section.hidden = true;
    return;
  }

  const select = document.getElementById("series-select");
  select.innerHTML = trend.metrics
    .map((m, i) => `<option value="${i}">${m.label}</option>`)
    .join("");
  select.addEventListener("change", () => renderTrendMetric(trend.metrics[select.selectedIndex]));

  renderTrendMetric(trend.metrics[0]);
}

function monthLabel(monthStr) {
  const [y, m] = monthStr.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1, 1));
  return d.toLocaleString("en-AU", { month: "short", timeZone: "UTC" }) + " " + String(y).slice(2);
}

function formatDelta(v) {
  const sign = v >= 0 ? "+" : "−";
  return `${sign}${Math.abs(v)}%`;
}

function renderTrendMetric(metric) {
  document.getElementById("trend-line-title").textContent =
    `Monthly job ads (3-month avg) · ${metric.label}`;

  const latestMonth = metric.history.length
    ? monthLabel(metric.history[metric.history.length - 1].month)
    : "latest";

  document.getElementById("trend-stats").innerHTML = `
    <div class="stat-tile big">
      <div class="tile-label">Ads · ${latestMonth}</div>
      <div class="tile-value">${metric.latest_level.toLocaleString()}</div>
    </div>
    <div class="stat-tile big">
      <div class="tile-label">Month on month</div>
      <div class="tile-value ${metric.mom_pct >= 0 ? "delta-good" : "delta-bad"}">${formatDelta(metric.mom_pct)}</div>
    </div>
    <div class="stat-tile big">
      <div class="tile-label">Year on year</div>
      <div class="tile-value ${metric.yoy_pct >= 0 ? "delta-good" : "delta-bad"}">${formatDelta(metric.yoy_pct)}</div>
    </div>
  `;

  if (trendLevelChart) { trendLevelChart.destroy(); trendLevelChart = null; }
  if (trendMomChart) { trendMomChart.destroy(); trendMomChart = null; }

  const hasHistory = metric.history && metric.history.length > 0;
  document.getElementById("chart-trend-level").hidden = !hasHistory;
  document.getElementById("trend-level-empty").hidden = hasHistory;
  document.getElementById("chart-trend-mom").hidden = !hasHistory;
  document.getElementById("trend-mom-empty").hidden = hasHistory;
  if (!hasHistory) return;

  const labels = metric.history.map((h) => monthLabel(h.month));
  const seriesColor = getSeriesColor();

  trendLevelChart = new Chart(document.getElementById("chart-trend-level"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: metric.label,
          data: metric.history.map((h) => h.level),
          borderColor: seriesColor,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHitRadius: 10,
          tension: 0.35,
          fill: false,
        },
      ],
    },
    options: baseOptions({
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { color: getMutedColor() }, beginAtZero: true, grid: { color: getBorderColor() } } },
    }),
  });

  const posColor = getSeriesColor();
  const negColor = getDivergingNegColor();

  trendMomChart = new Chart(document.getElementById("chart-trend-mom"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "MoM %",
          data: metric.history.map((h) => h.mom_pct),
          backgroundColor: metric.history.map((h) => (h.mom_pct >= 0 ? posColor : negColor)),
          borderRadius: 4,
          maxBarThickness: 24,
        },
      ],
    },
    options: baseOptions({
      plugins: {
        legend: { display: false },
        datalabels: {
          display: true,
          color: getMutedColor(),
          anchor: (ctx) => (ctx.dataset.data[ctx.dataIndex] >= 0 ? "end" : "start"),
          align: (ctx) => (ctx.dataset.data[ctx.dataIndex] >= 0 ? "end" : "start"),
          font: { size: 10 },
          formatter: (v) => formatDelta(v),
        },
      },
      scales: { y: { ticks: { color: getMutedColor(), callback: (v) => `${v}%` }, grid: { color: getBorderColor() } } },
    }),
  });
}

function getSeriesColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--series-1").trim();
}
function getDivergingNegColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--diverging-neg").trim();
}

// ---------- Live job ads dataset section ----------

function renderStats(s) {
  const tiles = [
    { value: s.totals.ads, label: "Total ads" },
    { value: s.totals.senior_plus, label: "Senior & above" },
    { value: s.totals.mid_junior, label: "Mid & junior" },
    { value: `${s.work_type.contract_pct}%`, label: "Contract roles" },
  ];
  if (s.salary?.median_aud) {
    tiles.push({ value: `$${Math.round(s.salary.median_aud / 1000)}k`, label: "Median salary" });
  }
  document.getElementById("stats").innerHTML = tiles
    .map((t) => `<div class="stat-tile"><div class="value">${t.value}</div><div class="label">${t.label}</div></div>`)
    .join("");
}

function baseOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: getTextColor() } } },
    scales: {
      x: { ticks: { color: getMutedColor() }, grid: { color: getBorderColor() } },
      y: { ticks: { color: getMutedColor() }, grid: { color: getBorderColor() } },
    },
    ...extra,
  };
}

function getTextColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--text").trim();
}
function getMutedColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim();
}
function getBorderColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--border").trim();
}

function renderLevel(s) {
  new Chart(document.getElementById("chart-level"), {
    type: "bar",
    data: {
      labels: s.level.map((l) => l.level),
      datasets: [{ label: "Ads", data: s.level.map((l) => l.ads), backgroundColor: PALETTE[0] }],
    },
    options: baseOptions({ plugins: { legend: { display: false } } }),
  });
}

function renderCloud(s) {
  new Chart(document.getElementById("chart-cloud"), {
    type: "bar",
    data: {
      labels: s.by_cloud.map((c) => c.cloud),
      datasets: [
        { label: "All ads", data: s.by_cloud.map((c) => c.ads), backgroundColor: PALETTE[0] },
        { label: "Senior+", data: s.by_cloud.map((c) => c.senior_plus ?? 0), backgroundColor: PALETTE[1] },
      ],
    },
    options: baseOptions(),
  });
}

function renderWeekly(s) {
  new Chart(document.getElementById("chart-weekly"), {
    type: "line",
    data: {
      labels: s.weekly_postings.map((w) => w.week_start),
      datasets: [{ label: "Ads posted", data: s.weekly_postings.map((w) => w.ads), borderColor: PALETTE[2], tension: 0.3 }],
    },
    options: baseOptions({ plugins: { legend: { display: false } } }),
  });
}

function renderBarPct(canvasId, rows, labelKey) {
  const sorted = [...rows].sort((a, b) => b.pct - a.pct).slice(0, 15);
  new Chart(document.getElementById(canvasId), {
    type: "bar",
    data: {
      labels: sorted.map((r) => r[labelKey]),
      datasets: [{ label: "% of ads", data: sorted.map((r) => r.pct), backgroundColor: PALETTE[4] }],
    },
    options: baseOptions({ indexAxis: "y", plugins: { legend: { display: false } } }),
  });
}

// Guarded startup: if Chart.js itself failed to load (CDN blocked, network
// issue, ad-blocker), show that plainly instead of letting a ReferenceError
// kill the whole script before any of the error handling below can run.
if (typeof Chart === "undefined") {
  document.getElementById("subtitle").textContent =
    "Failed to load Chart.js from the CDN — check your connection/ad-blocker and reload.";
} else {
  if (typeof ChartDataLabels !== "undefined") {
    Chart.register(ChartDataLabels);
    Chart.defaults.set("plugins.datalabels", { display: false });
  }
  main().catch((err) => {
    document.getElementById("subtitle").textContent = `Failed to load dashboard data: ${err.message}`;
  });
}
