import "./style.css";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});

const decimal = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const app = document.querySelector("#app");

function buildLookup(records) {
  const lookup = new Map();
  for (const record of records) {
    lookup.set(`${record.store_alias}|${record.dt}`, record);
  }
  return lookup;
}

function formatMetric(value, kind) {
  if (kind === "currency") return currency.format(value);
  if (kind === "percent") return percent.format(value);
  return decimal.format(value);
}

function createKpiCard(label, value, kind) {
  return `
    <article class="kpi-card">
      <p class="eyebrow">${label}</p>
      <p class="kpi-value">${formatMetric(value, kind)}</p>
    </article>
  `;
}

function createMiniBars(values, variant) {
  const maxValue = Math.max(...values, 0.0001);
  const bars = values
    .map((value, index) => {
      const height = Math.max(8, (value / maxValue) * 100);
      return `
        <div class="bar-slot">
          <div class="bar ${variant}" style="height:${height}%"></div>
          <span>${String(index).padStart(2, "0")}</span>
        </div>
      `;
    })
    .join("");

  return `<div class="mini-bars">${bars}</div>`;
}

function renderEvidence(record) {
  const salesCards = [
    ["Total Sales", record.sales.total_sales, "currency"],
    ["Avg / Product", record.sales.avg_sales_per_product, "currency"],
    ["Products", record.sales.product_count, "number"],
    ["Active Products", record.sales.active_product_count, "number"],
  ]
    .map(([label, value, kind]) => createKpiCard(label, value, kind))
    .join("");

  const pressureCards = [
    ["Stockout Rate", record.stockout.stockout_product_rate, "percent"],
    ["Severe Stockout", record.stockout.severe_stockout_product_rate, "percent"],
    ["Full Stockout", record.stockout.full_stockout_product_rate, "percent"],
    ["Avg Stockout Hours", record.stockout.avg_stockout_hours, "number"],
  ]
    .map(([label, value, kind]) => createKpiCard(label, value, kind))
    .join("");

  app.innerHTML = `
    <main class="shell">
      <section class="hero">
        <div>
          <p class="eyebrow">Retail Insight Agent</p>
          <h1>Evidence Viewer</h1>
          <p class="hero-copy">
            Read-only daily evidence across sales, stockout, discount, activity,
            holiday, and weather.
          </p>
        </div>
        <div class="hero-meta">
          <div>
            <span class="eyebrow">Store</span>
            <strong>${record.store_alias}</strong>
          </div>
          <div>
            <span class="eyebrow">Date</span>
            <strong>${record.dt}</strong>
          </div>
          <div>
            <span class="eyebrow">Holiday Label</span>
            <strong>${record.holiday.holiday_name_inferred.replaceAll("_", " ")}</strong>
          </div>
        </div>
      </section>

      <section class="controls" id="controls"></section>

      <section class="panel-grid">
        <section class="panel">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Sales</p>
              <h2>Daily sales profile</h2>
            </div>
          </header>
          <div class="kpi-grid">${salesCards}</div>
          ${createMiniBars(record.sales.hourly_sales, "sales-bar")}
        </section>

        <section class="panel">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Stockout</p>
              <h2>Availability pressure</h2>
            </div>
          </header>
          <div class="kpi-grid">${pressureCards}</div>
          ${createMiniBars(record.stockout.hourly_stockout_rate, "stockout-bar")}
        </section>

        <section class="panel compact">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Discount</p>
              <h2>Pricing state</h2>
            </div>
          </header>
          <dl class="metric-list">
            <div><dt>Average discount</dt><dd>${decimal.format(record.discount.avg_discount)}</dd></div>
            <div><dt>Discounted product rate</dt><dd>${percent.format(record.discount.discounted_product_rate)}</dd></div>
            <div><dt>Deep discount rate</dt><dd>${percent.format(record.discount.deep_discount_product_rate)}</dd></div>
          </dl>
        </section>

        <section class="panel compact">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Activity</p>
              <h2>Promotion participation</h2>
            </div>
          </header>
          <dl class="metric-list">
            <div><dt>Activity product rate</dt><dd>${percent.format(record.activity.activity_product_rate)}</dd></div>
            <div><dt>Activity sales share</dt><dd>${percent.format(record.activity.activity_sales_share)}</dd></div>
          </dl>
        </section>

        <section class="panel compact">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Calendar</p>
              <h2>Holiday context</h2>
            </div>
          </header>
          <dl class="metric-list">
            <div><dt>Weekday</dt><dd>${record.holiday.weekday}</dd></div>
            <div><dt>Weekend</dt><dd>${record.holiday.is_weekend ? "Yes" : "No"}</dd></div>
            <div><dt>Holiday flag</dt><dd>${record.holiday.holiday_flag ? "Yes" : "No"}</dd></div>
            <div><dt>Note</dt><dd class="note">${record.holiday.holiday_note}</dd></div>
          </dl>
        </section>

        <section class="panel compact">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Weather</p>
              <h2>Daily conditions</h2>
            </div>
          </header>
          <dl class="metric-list">
            <div><dt>Precipitation</dt><dd>${decimal.format(record.weather.precpt)}</dd></div>
            <div><dt>Temperature</dt><dd>${decimal.format(record.weather.avg_temperature)}</dd></div>
            <div><dt>Humidity</dt><dd>${decimal.format(record.weather.avg_humidity)}</dd></div>
            <div><dt>Wind level</dt><dd>${decimal.format(record.weather.avg_wind_level)}</dd></div>
          </dl>
        </section>
      </section>
    </main>
  `;
}

function renderControls(data, lookup) {
  const controls = document.querySelector("#controls");
  controls.innerHTML = `
    <label class="field">
      <span>Store Alias</span>
      <select id="store-select">
        ${data.stores.map((store) => `<option value="${store}">${store}</option>`).join("")}
      </select>
    </label>
    <label class="field">
      <span>Date</span>
      <select id="date-select">
        ${data.dates.map((dt) => `<option value="${dt}">${dt}</option>`).join("")}
      </select>
    </label>
  `;

  const storeSelect = document.querySelector("#store-select");
  const dateSelect = document.querySelector("#date-select");
  storeSelect.value = "h263";
  dateSelect.value = "2024-06-24";

  function update() {
    const key = `${storeSelect.value}|${dateSelect.value}`;
    const record = lookup.get(key);
    renderEvidence(record);
    renderControls(data, lookup);
    document.querySelector("#store-select").value = storeSelect.value;
    document.querySelector("#date-select").value = dateSelect.value;
    document.querySelector("#store-select").addEventListener("change", update);
    document.querySelector("#date-select").addEventListener("change", update);
  }

  storeSelect.addEventListener("change", update);
  dateSelect.addEventListener("change", update);
}

async function bootstrap() {
  const response = await fetch("/evidence_data.json");
  const data = await response.json();
  const lookup = buildLookup(data.records);
  renderEvidence(lookup.get("h263|2024-06-24"));
  renderControls(data, lookup);
}

bootstrap().catch((error) => {
  app.innerHTML = `
    <main class="shell">
      <section class="panel error-panel">
        <p class="eyebrow">Load error</p>
        <h1>Evidence data could not be loaded.</h1>
        <p>${error instanceof Error ? error.message : "Unknown error"}</p>
      </section>
    </main>
  `;
});
