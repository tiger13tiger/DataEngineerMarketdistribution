async function main() {
  let manifest;
  try {
    manifest = await fetchJSON("data/deltas/manifest.json");
  } catch {
    manifest = { deltas: [] };
  }
  const deltaRefs = manifest.deltas || [];

  if (deltaRefs.length === 0) {
    document.getElementById("subtitle").textContent =
      "No delta runs recorded yet — this fills in once the daily pipeline has run at least twice.";
    showEmpty("chart-ads-level-wrap", "ads-level-empty");
    showEmpty("chart-ads-delta-wrap", "ads-delta-empty");
    document.getElementById("delta-table-empty").hidden = false;
    document.getElementById("latest-delta-stats").innerHTML = "";
    return;
  }

  const records = await Promise.all(deltaRefs.map((d) => fetchJSON(d.file)));
  records.sort((a, b) => a.date.localeCompare(b.date));

  document.getElementById("subtitle").textContent =
    `${records.length} delta run${records.length === 1 ? "" : "s"} recorded — latest ${records[records.length - 1].date}`;

  renderLatestStats(records[records.length - 1]);
  renderAdsLevel(records);
  renderAdsDelta(records);
  renderDeltaTable(records);
}

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`);
  return res.json();
}

function showEmpty(wrapId, emptyId) {
  document.getElementById(wrapId).hidden = true;
  document.getElementById(emptyId).hidden = false;
}

function formatSigned(v) {
  const sign = v >= 0 ? "+" : "−";
  return `${sign}${Math.abs(v)}`;
}

function renderLatestStats(latest) {
  const tiles = [
    {
      value: formatSigned(latest.totals.ads.change),
      label: `Ads · ${latest.date}`,
      cls: latest.totals.ads.change >= 0 ? "delta-good" : "delta-bad",
    },
    {
      value: formatSigned(latest.totals.senior_plus.change),
      label: "Senior & above",
      cls: latest.totals.senior_plus.change >= 0 ? "delta-good" : "delta-bad",
    },
    {
      value: formatSigned(latest.totals.mid_junior.change),
      label: "Mid & junior",
      cls: latest.totals.mid_junior.change >= 0 ? "delta-good" : "delta-bad",
    },
    {
      value: `${formatSigned(latest.work_type.contract_pct.change)}pp`,
      label: "Contract %",
      cls: "",
    },
  ];
  document.getElementById("latest-delta-stats").innerHTML = tiles
    .map(
      (t) =>
        `<div class="stat-tile big"><div class="tile-label">${t.label}</div><div class="tile-value ${t.cls}">${t.value}</div></div>`
    )
    .join("");
}

function baseOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: getMutedColor() }, grid: { color: getBorderColor() } },
      y: { ticks: { color: getMutedColor() }, grid: { color: getBorderColor() } },
    },
    ...extra,
  };
}

function getMutedColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim();
}
function getBorderColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--border").trim();
}
function getSeriesColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--series-1").trim();
}
function getDivergingNegColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--diverging-neg").trim();
}

function renderAdsLevel(records) {
  // First point is the earliest run's starting level; the rest are each
  // subsequent run's resulting level - together a continuous day-by-day series.
  const labels = [records[0].from_id, ...records.map((r) => r.to_id)];
  const values = [records[0].totals.ads.from, ...records.map((r) => r.totals.ads.to)];
  new Chart(document.getElementById("chart-ads-level"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { data: values, borderColor: getSeriesColor(), borderWidth: 2, tension: 0.3, pointRadius: 3 },
      ],
    },
    options: baseOptions({
      scales: {
        y: { beginAtZero: true, ticks: { color: getMutedColor() }, grid: { color: getBorderColor() } },
        x: {
          ticks: { color: getMutedColor(), maxRotation: 45, minRotation: 45 },
          grid: { color: getBorderColor() },
        },
      },
    }),
  });
}

function renderAdsDelta(records) {
  const labels = records.map((r) => r.date);
  const values = records.map((r) => r.totals.ads.change);
  const posColor = getSeriesColor();
  const negColor = getDivergingNegColor();
  new Chart(document.getElementById("chart-ads-delta"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: values.map((v) => (v >= 0 ? posColor : negColor)),
          borderRadius: 4,
          maxBarThickness: 24,
        },
      ],
    },
    options: baseOptions(),
  });
}

function renderDeltaTable(records) {
  const rows = [...records].reverse();
  document.getElementById("delta-table-body").innerHTML = rows
    .map(
      (r) => `<tr>
        <td>${r.date}</td>
        <td>${formatSigned(r.totals.ads.change)}</td>
        <td>${formatSigned(r.totals.senior_plus.change)}</td>
        <td>${formatSigned(r.totals.mid_junior.change)}</td>
        <td>${formatSigned(r.work_type.contract_pct.change)}pp</td>
      </tr>`
    )
    .join("");
}

if (typeof Chart === "undefined") {
  document.getElementById("subtitle").textContent =
    "Failed to load Chart.js from the CDN — check your connection/ad-blocker and reload.";
} else {
  main().catch((err) => {
    document.getElementById("subtitle").textContent = `Failed to load delta data: ${err.message}`;
  });
}
