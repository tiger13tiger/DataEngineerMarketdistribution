const PALETTE = ["#3b6ef0", "#15b88a", "#d98c15", "#e0528a", "#8a5cf6", "#2fa9c9"];

async function main() {
  const manifest = await fetchJSON("data/manifest.json");
  const latest = manifest.snapshots[manifest.snapshots.length - 1];
  const snapshot = await fetchJSON(latest.data);

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

  renderStats(snapshot);
  renderLevel(snapshot);
  renderCloud(snapshot);
  renderOrEmpty("chart-weekly", snapshot.weekly_postings, () => renderWeekly(snapshot));
  renderOrEmpty("chart-trend", snapshot.monthly_trend?.ict_mom_history?.values, () => renderTrend(snapshot));
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

function renderTrend(s) {
  const hist = s.monthly_trend.ict_mom_history;
  new Chart(document.getElementById("chart-trend"), {
    type: "line",
    data: {
      labels: hist.months,
      datasets: [{ label: "MoM %", data: hist.values, borderColor: PALETTE[3], tension: 0.3 }],
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

main().catch((err) => {
  document.getElementById("subtitle").textContent = `Failed to load dashboard data: ${err.message}`;
});
