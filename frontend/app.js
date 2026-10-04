// NutriLens - Cyber-Kinetic Bio-Telemetry App Engine
const API_BASE = "/v1";

// Global App State
let currentTab = "dashboard";
let previousTab = "dashboard";
let currentDiaryDate = new Date().toISOString().split("T")[0];
let currentDetailFood = null;
let currentDetailGrams = 150;
let currentDetailUnit = "g";
let currentDetailVariant = null;
let currentSelectedFile = null;
let lastAnalysisResult = null;
let injectorCalories = 250;
let injectorMealPhase = "lunch";

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

function initApp() {
  switchTab("dashboard");
  fetchDailyTelemetry();
  setupSearchListener();
}

// -------------------------------------------------------------
// Navigation & Tab Switching
// -------------------------------------------------------------
function switchTab(tabId) {
  if (currentTab !== "food-detail") {
    previousTab = currentTab;
  }
  currentTab = tabId;
  document.querySelectorAll(".view-panel").forEach(panel => {
    panel.classList.add("hidden");
  });

  const activePanel = document.getElementById(`view-${tabId}`);
  if (activePanel) {
    activePanel.classList.remove("hidden");
  }

  // Update Header Title
  const titles = {
    "dashboard": "DASHBOARD",
    "quick-log": "QUICK SCAN",
    "food-detail": "CALIBRATION",
    "meals-diary": "MEALS DIARY",
    "nutrition-analytics": "ANALYTICS"
  };
  const titleEl = document.getElementById("header-title");
  if (titleEl) {
    titleEl.textContent = titles[tabId] || "NUTRILENS";
  }

  // Update Nav Links Active Style
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.remove("text-primary-container");
    link.classList.add("text-on-surface-variant");
  });
  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeNav) {
    activeNav.classList.add("text-primary-container");
    activeNav.classList.remove("text-on-surface-variant");
  }

  window.scrollTo({ top: 0, behavior: "smooth" });

  if (tabId === "dashboard" || tabId === "meals-diary") {
    fetchDailyTelemetry();
  }
}

function closeDetail() {
  switchTab(previousTab || "dashboard");
}

// -------------------------------------------------------------
// Daily Telemetry & Dashboard Data
// -------------------------------------------------------------
async function fetchDailyTelemetry() {
  try {
    const res = await fetch(`${API_BASE}/nutrition/daily?date=${currentDiaryDate}`);
    if (!res.ok) return;
    const data = await res.json();
    renderDashboard(data);
    renderDiary(data);
  } catch (err) {
    console.error("Error fetching daily telemetry:", err);
  }
}

function renderDashboard(data) {
  const totals = data.totals || {};
  const intakeKcal = Math.round(totals.energy_kcal?.value || 0);
  const targetKcal = 2150;
  const remaining = Math.max(0, targetKcal - intakeKcal);
  const budgetPercent = Math.max(0, Math.min(100, Math.round((remaining / targetKcal) * 100)));

  // Gauge & Calorie Remaining
  const calRemEl = document.getElementById("cal-remaining");
  if (calRemEl) calRemEl.textContent = remaining.toLocaleString();

  const budEl = document.getElementById("cal-budget-percent");
  if (budEl) budEl.textContent = `${budgetPercent}% BUDGET LEFT`;

  const intakeValEl = document.getElementById("intake-val");
  if (intakeValEl) intakeValEl.textContent = `-${intakeKcal.toLocaleString()}`;

  // Circular gauge arc offset calculation (dasharray 515)
  const arc = document.getElementById("gauge-arc");
  if (arc) {
    const progress = Math.min(1, intakeKcal / targetKcal);
    const offset = 515 - (515 * progress * 0.75); // partial gauge fill
    arc.style.strokeDashoffset = offset;
  }

  // Macros
  const protein = totals.protein_g?.value || 0;
  const carbs = totals.carbs_g?.value || 0;
  const fat = totals.fat_g?.value || 0;

  const pPercent = Math.min(100, Math.round((protein / 145) * 100));
  const cPercent = Math.min(100, Math.round((carbs / 220) * 100));
  const fPercent = Math.min(100, Math.round((fat / 65) * 100));

  const pStat = document.getElementById("protein-stat");
  if (pStat) pStat.innerHTML = `${Math.round(protein)}g <span class="text-outline">/ 145g</span> (${pPercent}%)`;
  const pBar = document.getElementById("protein-bar");
  if (pBar) pBar.style.width = `${pPercent}%`;

  const cStat = document.getElementById("carbs-stat");
  if (cStat) cStat.innerHTML = `${Math.round(carbs)}g <span class="text-outline">/ 220g</span> (${cPercent}%)`;
  const cBar = document.getElementById("carbs-bar");
  if (cBar) cBar.style.width = `${cPercent}%`;

  const fStat = document.getElementById("fat-stat");
  if (fStat) fStat.innerHTML = `${Math.round(fat)}g <span class="text-outline">/ 65g</span> (${fPercent}%)`;
  const fBar = document.getElementById("fat-bar");
  if (fBar) fBar.style.width = `${fPercent}%`;

  // Chrono Feed
  const container = document.getElementById("dashboard-meals-container");
  if (container) {
    if (!data.meals || data.meals.length === 0) {
      container.innerHTML = `
        <div class="p-space-md text-center bg-surface-container rounded-lg">
          <p class="font-label-sm text-on-surface-variant">NO MEALS RECORDED TODAY</p>
          <button onclick="switchTab('quick-log')" class="mt-2 text-primary-container font-label-sm uppercase font-bold hover:underline">
            + Scan First Meal
          </button>
        </div>`;
    } else {
      container.innerHTML = data.meals.slice(0, 3).map(m => {
        const itemNames = m.items.map(i => i.food_name).join(", ");
        const eatenTime = new Date(m.eaten_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return `
          <div class="flex items-center justify-between p-space-xs bg-surface-container rounded-lg">
            <div class="flex items-center gap-space-sm">
              <div class="w-12 h-12 rounded-lg bg-surface-container-high overflow-hidden shrink-0 flex items-center justify-center text-primary-container">
                <span class="material-symbols-outlined text-2xl">restaurant</span>
              </div>
              <div class="flex flex-col">
                <span class="font-label-md text-label-md font-bold text-on-surface uppercase">${m.meal_type}</span>
                <span class="font-body-sm text-body-sm text-on-surface-variant truncate max-w-[180px]">${itemNames}</span>
                <span class="font-label-sm text-label-sm text-outline font-mono">${eatenTime} HRS</span>
              </div>
            </div>
            <div class="flex flex-col items-end">
              <span class="font-label-lg text-label-lg font-bold text-on-surface">${Math.round(m.totals.energy_kcal?.value || 0)}</span>
              <span class="font-label-sm text-label-sm text-outline font-mono">KCAL</span>
            </div>
          </div>
        `;
      }).join("");
    }
  }
}

// -------------------------------------------------------------
// Meals Diary Render & Actions
// -------------------------------------------------------------
function renderDiary(data) {
  const intakeKcal = Math.round(data.totals?.energy_kcal?.value || 0);
  const diaryIntake = document.getElementById("diary-intake-kcal");
  if (diaryIntake) diaryIntake.textContent = intakeKcal.toLocaleString();

  const slots = {
    breakfast: document.getElementById("slot-breakfast-items"),
    lunch: document.getElementById("slot-lunch-items"),
    snack: document.getElementById("slot-snack-items"),
    dinner: document.getElementById("slot-dinner-items"),
  };

  const slotKcal = {
    breakfast: document.getElementById("brk-kcal"),
    lunch: document.getElementById("lun-kcal"),
    snack: document.getElementById("snk-kcal"),
    dinner: document.getElementById("din-kcal"),
  };

  // Reset slots
  Object.keys(slots).forEach(k => {
    if (slots[k]) slots[k].innerHTML = `<div class="text-on-surface-variant/60 font-label-sm text-center py-2">NO SPECIMENS RECORDED</div>`;
    if (slotKcal[k]) slotKcal[k].textContent = "0 KCAL";
  });

  if (!data.meals) return;

  const mealTotals = { breakfast: 0, lunch: 0, snack: 0, dinner: 0 };

  data.meals.forEach(meal => {
    const type = meal.meal_type.toLowerCase();
    const container = slots[type];
    if (container) {
      if (mealTotals[type] === 0) {
        container.innerHTML = "";
      }
      const kcal = Math.round(meal.totals?.energy_kcal?.value || 0);
      mealTotals[type] += kcal;

      meal.items.forEach(item => {
        const itemKcal = Math.round(item.nutrition_snapshot?.energy_kcal?.value || 0);
        const itemP = Math.round(item.nutrition_snapshot?.protein_g?.value || 0);
        const itemC = Math.round(item.nutrition_snapshot?.carbs_g?.value || 0);
        const itemF = Math.round(item.nutrition_snapshot?.fat_g?.value || 0);

        const row = document.createElement("div");
        row.className = "flex items-center justify-between p-2 rounded-lg bg-surface-container-high/60 hover:bg-surface-container-high transition-colors";
        row.innerHTML = `
          <div class="flex items-center gap-2 flex-1 min-w-0">
            <span class="w-1.5 h-1.5 rounded-full bg-primary-container"></span>
            <div class="flex flex-col truncate">
              <span class="font-label-md text-on-surface font-semibold truncate cursor-pointer hover:text-primary-container" onclick="openFoodDetail('${item.food_id}', '${item.variant_id || ''}', ${item.grams})">${item.food_name}</span>
              <span class="font-label-sm text-[11px] text-on-surface-variant font-mono">${item.grams}g // P:${itemP}g C:${itemC}g F:${itemF}g</span>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="font-label-md text-primary-container font-mono font-bold">${itemKcal} KCAL</span>
            <button onclick="deleteMealItem('${meal.id}')" class="text-on-surface-variant hover:text-error transition-colors p-1" title="Delete">
              <span class="material-symbols-outlined text-base">delete</span>
            </button>
          </div>
        `;
        container.appendChild(row);
      });
    }
  });

  Object.keys(slotKcal).forEach(k => {
    if (slotKcal[k]) slotKcal[k].textContent = `${mealTotals[k]} KCAL`;
  });
}

function changeDiaryDate(daysDelta) {
  const d = new Date(currentDiaryDate);
  d.setDate(d.getDate() + daysDelta);
  currentDiaryDate = d.toISOString().split("T")[0];

  const label = document.getElementById("diary-date-label");
  if (label) {
    const isToday = currentDiaryDate === new Date().toISOString().split("T")[0];
    const month = d.toLocaleString('default', { month: 'short' }).toUpperCase();
    const day = String(d.getDate()).padStart(2, '0');
    label.textContent = isToday ? `TODAY // ${day} ${month}` : `${day} ${month} 2026`;
  }
  fetchDailyTelemetry();
}

async function deleteMealItem(mealId) {
  if (!confirm("Remove this specimen entry from your daily telemetry?")) return;
  try {
    const res = await fetch(`${API_BASE}/meals/${mealId}`, { method: "DELETE" });
    if (res.ok) {
      fetchDailyTelemetry();
    }
  } catch (err) {
    console.error("Error deleting meal:", err);
  }
}

// -------------------------------------------------------------
// Food Scanning & AI Vision Pipeline
// -------------------------------------------------------------
function handleImageSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  currentSelectedFile = file;

  // Show preview in camera viewport
  const reader = new FileReader();
  reader.onload = function(e) {
    const feed = document.getElementById("camera-feed");
    if (feed) {
      feed.style.backgroundImage = `url('${e.target.result}')`;
    }
  };
  reader.readAsDataURL(file);
}

async function triggerAnalyze() {
  const btn = document.getElementById("instant-capture-btn");
  const originalText = btn.innerHTML;
  btn.innerHTML = `<span class="material-symbols-outlined text-lg animate-spin">refresh</span><span>PROCESSING AI...</span>`;
  btn.disabled = true;

  try {
    const formData = new FormData();
    if (currentSelectedFile) {
      formData.append("image", currentSelectedFile);
    } else {
      // Create synthetic meal image blob if user clicked Instant Scan directly
      const canvas = document.createElement("canvas");
      canvas.width = 600;
      canvas.height = 600;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#2c221b";
      ctx.fillRect(0, 0, 600, 600);
      // Draw plate
      ctx.fillStyle = "#8d7b68";
      ctx.beginPath();
      ctx.arc(300, 300, 240, 0, Math.PI * 2);
      ctx.fill();
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.9));
      formData.append("image", blob, "thali_scan.jpg");
    }

    formData.append("meta", JSON.stringify({
      captured_at: new Date().toISOString(),
      meal_type_hint: "lunch",
      client: { platform: "web", app_version: "1.0.0" }
    }));

    const res = await fetch(`${API_BASE}/food/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Scan failed: ${err.error?.message || "Could not analyze image"}`);
      return;
    }

    const data = await res.json();
    lastAnalysisResult = data;
    renderScanResults(data);
  } catch (err) {
    console.error("Scan error:", err);
    alert("Network error while communicating with AI service");
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function renderScanResults(data) {
  const container = document.getElementById("scan-results-container");
  const itemsList = document.getElementById("scan-detected-items");
  const countLabel = document.getElementById("detected-count");
  const bboxLayer = document.getElementById("bounding-boxes-layer");

  if (!container || !itemsList) return;
  container.classList.remove("hidden");
  itemsList.innerHTML = "";
  if (bboxLayer) bboxLayer.innerHTML = "";

  countLabel.textContent = `${data.items.length} SPECIMENS`;

  data.items.forEach(item => {
    // Render Bounding Box in HUD
    if (bboxLayer && item.region?.bbox) {
      const [ymin, xmin, ymax, xmax] = item.region.bbox;
      const box = document.createElement("div");
      box.className = "absolute border-2 border-primary-container bg-primary-container/10 rounded-sm";
      box.style.top = `${ymin * 100}%`;
      box.style.left = `${xmin * 100}%`;
      box.style.width = `${(xmax - xmin) * 100}%`;
      box.style.height = `${(ymax - ymin) * 100}%`;
      box.innerHTML = `<span class="absolute -top-5 left-0 bg-surface-container-high px-1.5 py-0.5 rounded text-[9px] font-mono text-primary-container font-bold uppercase">${item.food.name}</span>`;
      bboxLayer.appendChild(box);
    }

    // Render Item Card
    const kcal = Math.round(item.nutrition.energy_kcal?.value || 0);
    const p = Math.round(item.nutrition.protein_g?.value || 0);
    const c = Math.round(item.nutrition.carbs_g?.value || 0);
    const f = Math.round(item.nutrition.fat_g?.value || 0);
    const conf = item.food.confidence?.level || "high";
    const confScore = Math.round((item.food.confidence?.score || 0.9) * 100);

    const card = document.createElement("div");
    card.className = "w-full bg-surface-container-low rounded-xl p-space-sm flex flex-col gap-2 shadow-sm border border-surface-container hover:border-primary-container/50 transition-all";
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-primary-container"></span>
          <span class="font-headline-sm text-[16px] text-tertiary font-bold">${item.food.name}</span>
          <span class="font-label-sm text-[10px] px-1.5 py-0.5 rounded bg-surface-container text-primary-fixed-dim uppercase">${confScore}% CONF</span>
        </div>
        <button onclick="openFoodDetail('${item.food.food_id}', '${item.food.variant_id}', ${item.portion.grams})" class="text-primary-container font-label-sm uppercase hover:underline text-xs flex items-center gap-0.5">
          <span>CALIBRATE</span>
          <span class="material-symbols-outlined text-sm">tune</span>
        </button>
      </div>

      <div class="flex items-center justify-between text-on-surface-variant font-label-sm text-[12px] font-mono">
        <span>EST. PORTION: <strong class="text-on-surface">${item.portion.grams}g</strong> (${item.portion.unit.qty} ${item.portion.unit.unit})</span>
        <span class="text-primary-container font-bold">${kcal} KCAL</span>
      </div>

      <div class="w-full h-1.5 bg-surface-container-lowest rounded-full flex overflow-hidden gap-0.5">
        <div class="bg-error h-full" style="width: 25%" title="Protein ${p}g"></div>
        <div class="bg-secondary-container h-full" style="width: 50%" title="Carbs ${c}g"></div>
        <div class="bg-primary-container h-full" style="width: 25%" title="Fat ${f}g"></div>
      </div>

      <!-- Alternative Candidates Chips (FR-C1) -->
      ${item.food.alternatives && item.food.alternatives.length > 0 ? `
        <div class="flex items-center gap-1.5 pt-1 overflow-x-auto text-[11px] font-label-sm">
          <span class="text-outline text-[10px] uppercase">ALT:</span>
          ${item.food.alternatives.map(alt => `
            <button onclick="changeAnalyzedItemFood('${item.item_id}', '${alt.food_id}')" class="px-2 py-0.5 rounded bg-surface-container-high hover:bg-surface-bright text-on-surface hover:text-primary-container whitespace-nowrap">
              ${alt.name || alt.food_id}
            </button>
          `).join("")}
        </div>
      ` : ''}
    `;
    itemsList.appendChild(card);
  });
}

async function changeAnalyzedItemFood(itemId, newFoodId) {
  if (!lastAnalysisResult) return;
  try {
    const payload = {
      analysis_id: lastAnalysisResult.analysis_id,
      events: [
        {
          type: "food_changed",
          item_id: itemId,
          food_id: newFoodId,
          to: { food_id: newFoodId }
        }
      ]
    };
    const res = await fetch(`${API_BASE}/food/correct`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const corrData = await res.json();
      lastAnalysisResult = corrData.recalculated;
      renderScanResults(corrData.recalculated);
    }
  } catch (err) {
    console.error("Error applying correction:", err);
  }
}

async function commitScanToDiary() {
  if (!lastAnalysisResult || !lastAnalysisResult.items) return;
  const items = lastAnalysisResult.items.map(it => ({
    food_id: it.food.food_id,
    variant_id: it.food.variant_id,
    grams: it.portion.grams,
    unit: it.portion.unit.unit,
    unit_qty: it.portion.unit.qty,
    source: "ai",
    item_key: it.item_id
  }));

  try {
    const res = await fetch(`${API_BASE}/meals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_id: lastAnalysisResult.analysis_id,
        meal_type: injectorMealPhase || "lunch",
        items: items,
        notes: "Scan verified meal"
      })
    });
    if (res.ok) {
      alert("Meal successfully committed to daily telemetry!");
      switchTab("meals-diary");
      fetchDailyTelemetry();
    }
  } catch (err) {
    console.error("Error committing meal:", err);
  }
}

// -------------------------------------------------------------
// Food Detail Macro Calibration (Screen 3)
// -------------------------------------------------------------
async function openFoodDetail(foodId, variantId = null, initialGrams = 150) {
  try {
    const res = await fetch(`${API_BASE}/food/${foodId}`);
    if (!res.ok) return;
    const food = await res.json();
    currentDetailFood = food;
    currentDetailGrams = initialGrams;
    currentDetailVariant = variantId || (food.variants && food.variants.length > 0 ? food.variants[0].variant_id : `${foodId}:default`);

    // Populate Specimen View
    document.getElementById("detail-title").textContent = food.display_name;
    document.getElementById("detail-specimen-id").textContent = `SPECIMEN // ${food.food_id.substring(0, 8).toUpperCase()}`;
    document.getElementById("detail-category-badge").textContent = (food.category || "GENERAL").toUpperCase();

    // Set Slider value
    const slider = document.getElementById("portion-slider");
    if (slider) slider.value = currentDetailGrams;

    // Populate Units
    const unitsContainer = document.getElementById("detail-units-container");
    if (unitsContainer) {
      const units = food.serving_units || [];
      unitsContainer.innerHTML = units.map(u => `
        <button onclick="selectDetailUnit('${u.unit}', ${u.grams})" class="unit-chip px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface font-label-sm text-xs font-semibold whitespace-nowrap active:scale-95 transition-all">
          ${u.label || u.unit}
        </button>
      `).join("");
    }

    // Populate Variants (FR-C9)
    const variantsContainer = document.getElementById("detail-variants-container");
    if (variantsContainer) {
      variantsContainer.innerHTML = (food.variants || []).map(v => {
        const isCurrent = v.variant_id === currentDetailVariant;
        return `
          <button onclick="selectDetailVariant('${v.variant_id}')" class="p-2 rounded-lg text-left border ${isCurrent ? 'border-primary-container bg-surface-container-high' : 'border-surface-container bg-surface-container'} hover:border-primary-container/60 transition-all">
            <span class="font-label-sm font-bold text-on-surface block text-xs truncate">${v.label}</span>
            <span class="font-label-sm text-[10px] text-outline">${Math.round(v.energy_kcal)} kcal / 100g</span>
          </button>
        `;
      }).join("");
    }

    await recalculateDetailNutrition();
    switchTab("food-detail");
  } catch (err) {
    console.error("Error opening food detail:", err);
  }
}

function handleSliderChange(val) {
  currentDetailGrams = parseFloat(val);
  const label = document.getElementById("detail-grams-label");
  if (label) label.textContent = `${currentDetailGrams} GRAMS`;
  recalculateDetailNutrition();
}

function selectDetailUnit(unit, grams) {
  currentDetailUnit = unit;
  currentDetailGrams = grams;
  const slider = document.getElementById("portion-slider");
  if (slider) slider.value = grams;
  handleSliderChange(grams);
}

function selectDetailVariant(variantId) {
  currentDetailVariant = variantId;
  recalculateDetailNutrition();
  // Update button highlights
  if (currentDetailFood) {
    openFoodDetail(currentDetailFood.food_id, currentDetailVariant, currentDetailGrams);
  }
}

async function recalculateDetailNutrition() {
  if (!currentDetailFood) return;
  try {
    const payload = {
      items: [
        {
          food_id: currentDetailFood.food_id,
          variant_id: currentDetailVariant,
          quantity: currentDetailGrams,
          unit: "g"
        }
      ]
    };
    const res = await fetch(`${API_BASE}/nutrition/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) return;
    const calc = await res.json();
    const itemResult = calc.items[0];
    if (!itemResult) return;

    const nut = itemResult.nutrition;
    const kcal = Math.round(nut.energy_kcal?.value || 0);
    const p = (nut.protein_g?.value || 0).toFixed(1);
    const c = (nut.carbs_g?.value || 0).toFixed(1);
    const f = (nut.fat_g?.value || 0).toFixed(1);

    document.getElementById("detail-cal-display").textContent = kcal;
    document.getElementById("detail-quota-percent").textContent = `${Math.round((kcal / 2150) * 100)}%`;
    document.getElementById("detail-macro-protein").textContent = `${p}g`;
    document.getElementById("detail-macro-carbs").textContent = `${c}g`;
    document.getElementById("detail-macro-fat").textContent = `${f}g`;

    // Micronutrient Strata with availability flags (FR-N4)
    const microsContainer = document.getElementById("detail-micros-container");
    if (microsContainer && nut.micros) {
      microsContainer.innerHTML = Object.entries(nut.micros).map(([mKey, mVal]) => {
        const cleanName = mKey.replace("_mg", "").replace("_ug", "").replace("_", " ").toUpperCase();
        const unit = mKey.includes("_ug") ? "µg" : "mg";
        const isMissing = mVal.availability === "missing" || mVal.value === null;
        return `
          <div class="p-2 bg-surface-container rounded-lg flex items-center justify-between">
            <span class="font-label-sm text-outline text-[11px]">${cleanName}</span>
            <span class="font-label-sm font-bold text-xs ${isMissing ? 'text-outline/50 italic' : 'text-primary-container'} font-mono">
              ${isMissing ? 'NOT AVAILABLE' : `${mVal.value} ${unit}`}
            </span>
          </div>
        `;
      }).join("");
    }
  } catch (err) {
    console.error("Error recalculating nutrition:", err);
  }
}

async function confirmAndLogSpecimen() {
  if (!currentDetailFood) return;
  try {
    const mealPayload = {
      meal_type: injectorMealPhase || "lunch",
      items: [
        {
          food_id: currentDetailFood.food_id,
          variant_id: currentDetailVariant,
          grams: currentDetailGrams,
          unit: currentDetailUnit || "g",
          unit_qty: currentDetailGrams,
          source: "user_corrected"
        }
      ],
      notes: "Calibrated manual specimen"
    };
    const res = await fetch(`${API_BASE}/meals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(mealPayload)
    });
    if (res.ok) {
      alert(`Specimen ${currentDetailFood.display_name} successfully added to diary!`);
      switchTab("meals-diary");
      fetchDailyTelemetry();
    }
  } catch (err) {
    console.error("Error logging specimen:", err);
  }
}

// -------------------------------------------------------------
// Universal Search Bar & Manual Food Search
// -------------------------------------------------------------
let searchDebounceTimer = null;

function setupSearchListener() {
  const searchInput = document.getElementById("food-search-input");
  const dropdown = document.getElementById("search-results-dropdown");
  const clearBtn = document.getElementById("clear-search-btn");

  if (!searchInput) return;

  searchInput.addEventListener("input", (e) => {
    const query = e.target.value.trim();
    if (query.length > 0 && clearBtn) clearBtn.classList.remove("hidden");
    else if (clearBtn) clearBtn.classList.add("hidden");

    clearTimeout(searchDebounceTimer);
    if (query.length < 1) {
      if (dropdown) dropdown.classList.add("hidden");
      return;
    }

    searchDebounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/food/search?q=${encodeURIComponent(query)}&limit=8`);
        if (!res.ok) return;
        const foods = await res.json();
        renderSearchDropdown(foods);
      } catch (err) {
        console.error("Search error:", err);
      }
    }, 200);
  });
}

function renderSearchDropdown(foods) {
  const dropdown = document.getElementById("search-results-dropdown");
  if (!dropdown) return;

  if (foods.length === 0) {
    dropdown.innerHTML = `<div class="p-3 text-center text-outline font-label-sm text-xs">NO CANONICAL FOODS MATCHED</div>`;
    dropdown.classList.remove("hidden");
    return;
  }

  dropdown.innerHTML = foods.map(f => `
    <div onclick="openFoodDetail('${f.food_id}'); clearSearch();" class="p-2.5 rounded-lg bg-surface-container hover:bg-surface-container-highest cursor-pointer flex items-center justify-between transition-colors">
      <div class="flex flex-col">
        <span class="font-label-md font-bold text-on-surface text-xs">${f.display_name}</span>
        <span class="font-label-sm text-[10px] text-outline">${f.category} // ${f.default_unit}</span>
      </div>
      <div class="flex flex-col items-end">
        <span class="font-label-md text-primary-container font-bold text-xs font-mono">${Math.round(f.energy_kcal_per_100g)} KCAL</span>
        <span class="font-label-sm text-[9px] text-outline">per 100g</span>
      </div>
    </div>
  `).join("");
  dropdown.classList.remove("hidden");
}

function clearSearch() {
  const searchInput = document.getElementById("food-search-input");
  const dropdown = document.getElementById("search-results-dropdown");
  const clearBtn = document.getElementById("clear-search-btn");
  if (searchInput) searchInput.value = "";
  if (dropdown) dropdown.classList.add("hidden");
  if (clearBtn) clearBtn.classList.add("hidden");
}

// -------------------------------------------------------------
// Rapid Calorie Injector & Helpers
// -------------------------------------------------------------
function adjustInjector(delta) {
  injectorCalories = Math.max(50, injectorCalories + delta);
  const disp = document.getElementById("calorie-display");
  if (disp) disp.textContent = injectorCalories;
}

function selectMealPhase(phase, btn) {
  injectorMealPhase = phase;
  document.querySelectorAll(".meal-phase-btn").forEach(b => {
    b.className = "meal-phase-btn bg-surface-container-highest text-on-surface py-2 rounded-lg font-label-sm text-label-sm uppercase tracking-wider transition-colors active:scale-95";
  });
  if (btn) {
    btn.className = "meal-phase-btn bg-primary-container text-on-primary font-bold py-2 rounded-lg font-label-sm text-label-sm uppercase tracking-wider transition-colors active:scale-95 shadow-[0_0_8px_rgba(0,255,136,0.3)]";
  }
}

async function commitQuickInjector() {
  try {
    const res = await fetch(`${API_BASE}/meals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        meal_type: injectorMealPhase,
        items: [
          {
            food_id: "roti_plain",
            grams: Math.round(injectorCalories / 2.5),
            unit: "g",
            source: "manual"
          }
        ],
        notes: `Rapid Injected ${injectorCalories} kcal`
      })
    });
    if (res.ok) {
      alert(`+${injectorCalories} KCAL committed to daily telemetry!`);
      switchTab("dashboard");
      fetchDailyTelemetry();
    }
  } catch (err) {
    console.error("Error committing injector:", err);
  }
}

function promptAddFoodToSlot(slot) {
  injectorMealPhase = slot;
  switchTab("quick-log");
  const searchInput = document.getElementById("food-search-input");
  if (searchInput) {
    searchInput.focus();
    searchInput.placeholder = `SEARCH FOOD FOR ${slot.toUpperCase()}...`;
  }
}

function openManualFoodModal() {
  switchTab("quick-log");
  const searchInput = document.getElementById("food-search-input");
  if (searchInput) searchInput.focus();
}

function openProfileModal() {
  openModelOpsModal();
}

async function checkHealth() {
  const radar = document.getElementById("radar-icon");
  if (radar) radar.classList.add("animate-spin");
  try {
    const res = await fetch(`${API_BASE}/ready`);
    const data = await res.json();
    alert(`System Health: ${data.status.toUpperCase()} // Database: ${data.database} // AI Models Active.`);
  } catch (err) {
    alert("System health check failed: backend unreachable.");
  } finally {
    if (radar) radar.classList.remove("animate-spin");
  }
}

// -------------------------------------------------------------
// Mobile App Modal Handlers
// -------------------------------------------------------------
function openMobileAppModal() {
  const modal = document.getElementById("modal-mobile-app");
  if (modal) modal.classList.remove("hidden");
}

function closeMobileAppModal() {
  const modal = document.getElementById("modal-mobile-app");
  if (modal) modal.classList.add("hidden");
}

// -------------------------------------------------------------
// Phase 9: Model Improvement & Reviewer Hub Handlers
// -------------------------------------------------------------
function openModelOpsModal() {
  const modal = document.getElementById("modal-model-ops");
  if (modal) modal.classList.remove("hidden");
  switchOpsTab("registry");
}

function closeModelOpsModal() {
  const modal = document.getElementById("modal-model-ops");
  if (modal) modal.classList.add("hidden");
}

function switchOpsTab(tab) {
  const tabs = ["registry", "etl", "analytics", "consent"];
  tabs.forEach(t => {
    const btn = document.getElementById(`opstab-${t}`);
    const panel = document.getElementById(`opspanel-${t}`);
    if (btn && panel) {
      if (t === tab) {
        btn.classList.add("text-primary-container", "border-primary-container");
        btn.classList.remove("text-on-surface-variant", "border-transparent");
        panel.classList.remove("hidden");
      } else {
        btn.classList.remove("text-primary-container", "border-primary-container");
        btn.classList.add("text-on-surface-variant", "border-transparent");
        panel.classList.add("hidden");
      }
    }
  });

  if (tab === "registry") loadModelRegistry();
  if (tab === "etl") loadPendingReviews();
  if (tab === "analytics") loadErrorAnalytics();
  if (tab === "consent") loadUserConsent();
}

async function loadModelRegistry() {
  const container = document.getElementById("ops-model-list");
  if (!container) return;
  try {
    const res = await fetch(`${API_BASE}/admin/models`);
    const data = await res.json();
    const models = data.models || [];
    if (models.length === 0) {
      container.innerHTML = `<div class="p-3 text-center text-xs font-mono text-outline">No models found in registry.</div>`;
      return;
    }
    container.innerHTML = models.map(m => {
      const isProd = m.stage === "production";
      const isCanary = m.stage === "canary";
      const badgeColor = isProd ? "bg-primary-container text-on-primary font-bold" : (isCanary ? "bg-secondary-fixed-dim text-on-secondary-fixed font-bold" : "bg-surface-container-highest text-outline");
      const metricsText = m.metrics ? Object.entries(m.metrics).map(([k, v]) => `${k}:${typeof v === 'number' ? v.toFixed(2) : v}`).join(" | ") : "N/A";
      return `
        <div class="p-3 rounded-xl bg-surface-container-low border border-surface-bright flex items-center justify-between">
          <div class="space-y-0.5">
            <div class="flex items-center gap-2">
              <span class="font-mono text-xs font-bold text-on-surface">${m.id}</span>
              <span class="px-2 py-0.5 rounded text-[10px] uppercase ${badgeColor}">${m.stage} ${m.active_traffic_pct ? `[${m.active_traffic_pct}%]` : ''}</span>
              <span class="text-[10px] text-outline font-mono uppercase">${m.kind}</span>
            </div>
            <div class="text-[11px] text-on-surface-variant font-mono">${metricsText}</div>
            <div class="text-[10px] text-outline">${m.notes || ''}</div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-3 text-center text-xs font-mono text-error">Failed to load registry: ${err.message}</div>`;
  }
}

async function runFeedbackETL() {
  const btn = document.getElementById("btn-run-etl");
  const statsBox = document.getElementById("etl-stats-box");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/admin/feedback/etl`, { method: "POST" });
    const data = await res.json();
    const s = data.summary || {};
    if (statsBox) {
      statsBox.classList.remove("hidden");
      document.getElementById("etl-proc-val").textContent = s.processed || 0;
      document.getElementById("etl-queue-val").textContent = s.queued || 0;
      document.getElementById("etl-rej-val").textContent = s.auto_rejected || 0;
      document.getElementById("etl-consent-val").textContent = s.consent_declined || 0;
    }
    loadPendingReviews();
  } catch (err) {
    alert(`ETL Failed: ${err.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadPendingReviews() {
  const container = document.getElementById("ops-pending-list");
  if (!container) return;
  try {
    const res = await fetch(`${API_BASE}/admin/feedback/pending`);
    const data = await res.json();
    const items = data.items || [];
    if (items.length === 0) {
      container.innerHTML = `<div class="p-4 text-center text-xs font-mono text-outline rounded-lg bg-surface-container-low border border-surface-bright">All correction events reviewed. Zero queued items.</div>`;
      return;
    }
    container.innerHTML = items.map(item => `
      <div class="p-3 rounded-xl bg-surface-container-low border border-surface-bright space-y-2">
        <div class="flex items-center justify-between text-xs font-mono">
          <span class="text-primary-container font-semibold uppercase">${item.event_type}</span>
          <span class="px-2 py-0.5 rounded bg-surface-container text-on-surface-variant text-[10px] uppercase">${item.inferred_cause}</span>
        </div>
        <div class="grid grid-cols-2 gap-2 text-xs font-mono bg-surface p-2 rounded-lg">
          <div><span class="text-outline block text-[10px]">BEFORE (AI)</span>${JSON.stringify(item.before)}</div>
          <div><span class="text-primary-container block text-[10px]">AFTER (USER)</span>${JSON.stringify(item.after)}</div>
        </div>
        <div class="flex justify-end gap-2 pt-1">
          <button onclick="submitReviewAction('${item.correction_id}', 'rejected', '${item.inferred_cause}')" class="px-3 py-1 rounded bg-surface-container hover:bg-surface-bright text-error text-xs font-mono font-semibold">REJECT</button>
          <button onclick="submitReviewAction('${item.correction_id}', 'accepted', '${item.inferred_cause}')" class="px-3 py-1 rounded bg-primary-container text-on-primary text-xs font-mono font-bold hover:bg-primary-fixed-dim">APPROVE &amp; QUEUE FOR RETRAINING</button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-3 text-center text-xs font-mono text-error">Failed to load pending reviews: ${err.message}</div>`;
  }
}

async function submitReviewAction(correctionId, decision, cause) {
  try {
    const res = await fetch(`${API_BASE}/admin/feedback/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        correction_id: correctionId,
        decision: decision,
        cause: cause,
        notes: `Reviewer marked ${decision} via dashboard`,
      }),
    });
    if (res.ok) {
      loadPendingReviews();
    } else {
      const err = await res.json();
      alert(`Action failed: ${err.detail || 'Error'}`);
    }
  } catch (err) {
    alert(`Review submission failed: ${err.message}`);
  }
}

async function triggerBuildDataset() {
  const input = document.getElementById("new-dataset-id");
  const versionId = input ? input.value.trim() : "";
  if (!versionId) {
    alert("Please enter a dataset version tag (e.g. ds-2026.02)");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/admin/datasets/build`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        version_id: versionId,
        notes: "Immutable dataset snapshot created via Reviewer Hub",
      }),
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Dataset ${versionId} snapshot successfully generated with ${data.dataset.total_samples} samples!`);
      if (input) input.value = "";
    } else {
      const err = await res.json();
      alert(`Build failed: ${err.detail || 'Error'}`);
    }
  } catch (err) {
    alert(`Snapshot error: ${err.message}`);
  }
}

async function loadErrorAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/admin/analytics/errors`);
    const data = await res.json();
    const a = data.analytics || {};
    const biasEl = document.getElementById("portion-bias-val");
    const corrEl = document.getElementById("total-corr-val");
    if (biasEl) biasEl.textContent = `${a.portion_bias_mean_pct_error || 0.0}%`;
    if (corrEl) corrEl.textContent = a.total_corrections_analyzed || 0;

    const pairsList = document.getElementById("confusion-pairs-list");
    if (pairsList) {
      const pairs = a.top_confusion_pairs || [];
      if (pairs.length === 0) {
        pairsList.innerHTML = `<div class="text-outline">No confusion events logged yet.</div>`;
      } else {
        pairsList.innerHTML = pairs.map(p => `
          <div class="flex items-center justify-between p-2 rounded bg-surface">
            <span class="text-on-surface">${p.pair}</span>
            <span class="text-primary-container font-bold">${p.count}x</span>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

async function loadUserConsent() {
  try {
    const res = await fetch(`${API_BASE}/users/me`);
    if (res.ok) {
      const u = await res.json();
      const toggle = document.getElementById("consent-toggle");
      if (toggle) toggle.checked = !!u.training_consent;
    }
  } catch (err) {
    console.error("Error loading consent:", err);
  }
}

async function toggleTrainingConsent(checked) {
  try {
    await fetch(`${API_BASE}/users/me/consent`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ training_consent: checked }),
    });
  } catch (err) {
    console.error("Error updating consent:", err);
  }
}

