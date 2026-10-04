/**
 * NutriScan AI — Frontend Application
 * Handles image upload, text analysis, results rendering,
 * user profile management, and food history.
 */

'use strict';

// ─── State ────────────────────────────────────────────────────────────────────
const state = {
  userId: localStorage.getItem('nutriscan_user_id') || 'anonymous',
  currentResult: null,
  currentRecTab: 'tips',
  profile: JSON.parse(localStorage.getItem('nutriscan_profile') || 'null'),
  history: JSON.parse(localStorage.getItem('nutriscan_history') || '[]'),
};

// ─── API Config ───────────────────────────────────────────────────────────────
const API_BASE = window.location.origin + '/api';

// ─── DOM Elements ─────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const uploadZone     = $('uploadZone');
const uploadInner    = $('uploadInner');
const previewContainer = $('previewContainer');
const imagePreview   = $('imagePreview');
const fileInput      = $('fileInput');
const btnClearImage  = $('btnClearImage');
const btnAnalyzeImage = $('btnAnalyzeImage');
const btnAnalyzeText = $('btnAnalyzeText');
const foodNameInput  = $('foodNameInput');
const portionInput   = $('portionInput');
const ingredientsInput = $('ingredientsInput');
const loadingCard    = $('loadingCard');
const resultsSection = $('results');

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupImageUpload();
  setupTextInput();
  setupRecTabs();
  setupProfile();
  loadProfileFromStorage();
});

// ─── Tab Switching ────────────────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      $(`tab-${target}`).classList.add('active');
    });
  });
}

// ─── Image Upload ─────────────────────────────────────────────────────────────
function setupImageUpload() {
  // File input change
  fileInput.addEventListener('change', e => {
    if (e.target.files[0]) showImagePreview(e.target.files[0]);
  });

  // Click zone
  uploadInner.addEventListener('click', () => fileInput.click());

  // Drag & drop
  uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) showImagePreview(file);
    else showToast('⚠️ Please drop an image file (PNG, JPG, WEBP)');
  });

  // Clear
  btnClearImage.addEventListener('click', clearImage);

  // Analyze button
  btnAnalyzeImage.addEventListener('click', analyzeImage);
}

function showImagePreview(file) {
  const reader = new FileReader();
  reader.onload = e => {
    imagePreview.src = e.target.result;
    uploadInner.style.display = 'none';
    previewContainer.style.display = 'block';
    btnAnalyzeImage.disabled = false;
    fileInput._file = file;
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  imagePreview.src = '';
  uploadInner.style.display = 'block';
  previewContainer.style.display = 'none';
  btnAnalyzeImage.disabled = true;
  fileInput.value = '';
  fileInput._file = null;
}

// ─── Text Input & Autocomplete ────────────────────────────────────────────────
const FOOD_SUGGESTIONS = [
  'Pizza', 'Burger', 'Sushi', 'Salad', 'Pasta', 'Steak', 'Chicken Curry',
  'Ramen', 'Tacos', 'Caesar Salad', 'Grilled Salmon', 'French Fries',
  'Omelette', 'Pancakes', 'Greek Salad', 'Hummus', 'Guacamole', 'Edamame',
  'Pad Thai', 'Lasagna', 'Cheesecake', 'Tiramisu', 'Donuts', 'Waffles',
  'Miso Soup', 'Spring Rolls', 'Falafel', 'Samosa', 'Ice Cream', 'Hot Dog',
  'Nachos', 'Risotto', 'Clam Chowder', 'Fried Rice', 'Pho', 'Baklava',
];

function setupTextInput() {
  const autocomplete = $('autocomplete');

  foodNameInput.addEventListener('input', () => {
    const q = foodNameInput.value.trim().toLowerCase();
    if (q.length < 2) { autocomplete.style.display = 'none'; return; }

    const matches = FOOD_SUGGESTIONS.filter(f => f.toLowerCase().includes(q)).slice(0, 6);
    if (!matches.length) { autocomplete.style.display = 'none'; return; }

    autocomplete.innerHTML = matches.map(m =>
      `<div class="autocomplete-item" onclick="selectFood('${m}')">${m}</div>`
    ).join('');
    autocomplete.style.display = 'block';
  });

  document.addEventListener('click', e => {
    if (!foodNameInput.contains(e.target)) autocomplete.style.display = 'none';
  });

  foodNameInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { autocomplete.style.display = 'none'; analyzeText(); }
  });

  btnAnalyzeText.addEventListener('click', analyzeText);
}

function selectFood(name) {
  foodNameInput.value = name;
  $('autocomplete').style.display = 'none';
}

// ─── Recommendation Tabs ──────────────────────────────────────────────────────
function setupRecTabs() {
  document.querySelectorAll('.rec-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.rec-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.currentRecTab = tab.dataset.rec;
      if (state.currentResult) renderRecTab(state.currentResult.recommendations);
    });
  });
}

// ─── API Calls ────────────────────────────────────────────────────────────────
async function analyzeImage() {
  const file = fileInput._file;
  if (!file) { showToast('⚠️ Please select an image first'); return; }

  const formData = new FormData();
  formData.append('image', file);
  formData.append('user_id', state.userId);

  showLoading('Recognizing food from image...');

  try {
    const res = await fetch(`${API_BASE}/predict`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Prediction failed');
    handleResult(data, 'image');
  } catch (err) {
    hideLoading();
    showToast(`❌ ${err.message}`);
  }
}

async function analyzeText() {
  const foodName = foodNameInput.value.trim();
  const ingredients = ingredientsInput.value.trim();
  const portion = parseInt(portionInput.value) || 100;

  if (!foodName && !ingredients) {
    showToast('⚠️ Please enter a food name or ingredients');
    return;
  }

  const payload = {
    user_id: state.userId,
    portion_size: portion,
  };
  if (foodName) payload.food_name = foodName;
  if (ingredients) payload.ingredients = ingredients.split(',').map(s => s.trim()).filter(Boolean);

  showLoading('Analyzing nutritional content...');

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Analysis failed');
    handleResult(data, 'text');
  } catch (err) {
    hideLoading();
    // Fallback: use local computation if API not available
    try {
      const localResult = computeLocalResult(foodName || ingredients, portion);
      handleResult(localResult, 'text');
    } catch (localErr) {
      showToast(`❌ ${err.message}`);
    }
  }
}

// ─── Local Fallback Computation ───────────────────────────────────────────────
const LOCAL_NUTRITION = {
  'pizza': {calories:266,protein:11,fat:10,carbohydrates:33,fiber:2.3,sugar:3.6,sodium:598,cholesterol:17},
  'burger': {calories:295,protein:17,fat:14,carbohydrates:24,fiber:1,sugar:5,sodium:500,cholesterol:55},
  'sushi': {calories:140,protein:5.5,fat:3.5,carbohydrates:21,fiber:0.6,sugar:2.5,sodium:300,cholesterol:15},
  'salad': {calories:52,protein:3,fat:2,carbohydrates:6,fiber:2.5,sugar:3,sodium:180,cholesterol:5},
  'pasta': {calories:131,protein:5,fat:1.1,carbohydrates:25,fiber:1.8,sugar:0.6,sodium:1,cholesterol:0},
  'steak': {calories:271,protein:26,fat:18,carbohydrates:0,fiber:0,sugar:0,sodium:59,cholesterol:78},
  'chicken': {calories:165,protein:31,fat:3.6,carbohydrates:0,fiber:0,sugar:0,sodium:74,cholesterol:85},
  'ramen': {calories:147,protein:9,fat:4,carbohydrates:20,fiber:1,sugar:2,sodium:1890,cholesterol:35},
  'tacos': {calories:210,protein:11,fat:9,carbohydrates:21,fiber:2,sugar:2,sodium:390,cholesterol:30},
  'default': {calories:200,protein:8,fat:8,carbohydrates:25,fiber:2,sugar:5,sodium:300,cholesterol:30},
};

function computeLocalResult(foodName, portionG) {
  const key = Object.keys(LOCAL_NUTRITION).find(k => foodName.toLowerCase().includes(k)) || 'default';
  const base = LOCAL_NUTRITION[key];
  const scale = portionG / 100;
  const n = {};
  Object.keys(base).forEach(k => n[k] = +(base[k] * scale).toFixed(1));
  n.portion_g = portionG;
  n.glycemic_index = 50;
  n.vitamins = {};
  n.minerals = {};

  // Simple health scoring
  let score = 100;
  if (n.sugar > 15) score -= 20;
  if (n.sodium > 600) score -= 20;
  if (n.fat > 20) score -= 15;
  if (n.protein > 20) score += 10;
  if (n.fiber > 5) score += 8;
  score = Math.max(0, Math.min(100, score));

  const label = score >= 70 ? 'Healthy' : score >= 45 ? 'Moderate' : 'Unhealthy';

  return {
    status: 'success',
    input_type: 'text',
    food_name: foodName,
    nutrition: n,
    health_score: {
      score, label,
      color: label === 'Healthy' ? '#22c55e' : label === 'Moderate' ? '#f59e0b' : '#ef4444',
      emoji: label === 'Healthy' ? '✅' : label === 'Moderate' ? '⚠️' : '❌',
      risks: n.sodium > 600 ? [{risk:'High Sodium',level:'Moderate',reason:'Sodium exceeds recommended daily limits',icon:'🧂'}] : [],
      benefits: n.protein > 15 ? ['Good protein source'] : [],
      nutrient_breakdown: {
        calories_percent: +(n.calories / 2000 * 100).toFixed(1),
        protein_percent: +(n.protein / 50 * 100).toFixed(1),
        fat_percent: +(n.fat / 65 * 100).toFixed(1),
        carbs_percent: +(n.carbohydrates / 300 * 100).toFixed(1),
        fiber_percent: +(n.fiber / 28 * 100).toFixed(1),
        sodium_percent: +(n.sodium / 2300 * 100).toFixed(1),
      }
    },
    recommendations: {
      general_tips: n.sugar > 10 ? ['🍭 Reduce sugar intake for better metabolic health'] : ['✅ Reasonable nutritional profile'],
      healthier_alternatives: ['Try grilled instead of fried', 'Add a side of vegetables'],
      lifestyle_tips: ['💧 Stay hydrated with 8 glasses of water daily'],
      meal_pairing: ['Pair with a fiber-rich salad for balance'],
      portion_advice: `A ${portionG}g serving. Adjust based on your daily caloric needs.`,
      personalized_advice: ['Create a profile for personalized health recommendations! 👤'],
    },
    timestamp: new Date().toISOString(),
  };
}

// ─── Result Handling ──────────────────────────────────────────────────────────
function handleResult(data, inputType) {
  state.currentResult = data;
  hideLoading();
  renderResults(data, inputType);
  addToLocalHistory(data);
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderResults(data, inputType) {
  resultsSection.style.display = 'block';

  const n = data.nutrition;
  const h = data.health_score;

  // Food identity
  $('foodEmoji').textContent = getFoodEmoji(data.food_name);
  $('foodName').textContent = data.food_name;

  if (inputType === 'image' && data.confidence) {
    $('foodConfidence').textContent = `AI Confidence: ${data.confidence}%`;
  } else {
    $('foodConfidence').textContent = `${n.portion_g || 100}g serving · Nutritional analysis`;
  }

  // Health badge
  const badge = $('healthBadge');
  $('healthEmoji').textContent = h.emoji;
  $('healthLabel').textContent = h.label;
  badge.style.borderColor = h.color;
  $('healthLabel').style.color = h.color;

  // Score meter
  const scoreFill = $('scoreFill');
  const scoreColor = h.score >= 70 ? 'linear-gradient(90deg,#22c55e,#4ade80)' :
                     h.score >= 45 ? 'linear-gradient(90deg,#f59e0b,#fbbf24)' :
                     'linear-gradient(90deg,#ef4444,#f87171)';
  scoreFill.style.background = scoreColor;
  setTimeout(() => { scoreFill.style.width = `${h.score}%`; }, 100);
  $('scoreValue').textContent = `${h.score}/100`;
  $('scoreValue').style.color = h.color;

  // Macros
  renderMacros(n);

  // Daily values
  renderDailyValues(h.nutrient_breakdown || {});

  // Risks
  renderRisks(h.risks || []);

  // Recommendations
  renderRecTab(data.recommendations);

  // Predictions (image only)
  if (inputType === 'image' && data.top_predictions?.length) {
    $('predictionsCard').style.display = 'block';
    renderPredictions(data.top_predictions);
  } else {
    $('predictionsCard').style.display = 'none';
  }

  // Animate in
  resultsSection.querySelectorAll('.card').forEach((card, i) => {
    card.style.animationDelay = `${i * 0.08}s`;
    card.style.animation = 'none';
    void card.offsetHeight;
    card.style.animation = '';
  });
}

function renderMacros(n) {
  const macros = [
    { icon: '🔥', value: Math.round(n.calories), unit: 'kcal', name: 'Calories', color: '#ff6b6b' },
    { icon: '💪', value: `${n.protein}g`, unit: 'protein', name: 'Protein', color: '#63fcb6' },
    { icon: '🌾', value: `${n.carbohydrates}g`, unit: 'carbs', name: 'Carbs', color: '#ffb347' },
    { icon: '🥑', value: `${n.fat}g`, unit: 'fat', name: 'Fat', color: '#3db8ff' },
    { icon: '🌿', value: `${n.fiber}g`, unit: 'fiber', name: 'Fiber', color: '#a78bfa' },
    { icon: '🍬', value: `${n.sugar}g`, unit: 'sugar', name: 'Sugar', color: '#f472b6' },
    { icon: '🧂', value: `${Math.round(n.sodium)}mg`, unit: 'sodium', name: 'Sodium', color: '#94a3b8' },
    { icon: '🫀', value: `${Math.round(n.cholesterol)}mg`, unit: '', name: 'Cholesterol', color: '#fb923c' },
  ];

  $('macroGrid').innerHTML = macros.map(m => `
    <div class="macro-item">
      <span class="macro-icon">${m.icon}</span>
      <span class="macro-value" style="color:${m.color}">${m.value}</span>
      <span class="macro-name">${m.name}</span>
      ${m.unit ? `<span class="macro-unit">${m.unit}</span>` : ''}
    </div>
  `).join('');
}

function renderDailyValues(breakdown) {
  const dvItems = [
    { label: 'Calories',  key: 'calories_percent',  color: '#ff6b6b' },
    { label: 'Protein',   key: 'protein_percent',   color: '#63fcb6' },
    { label: 'Carbs',     key: 'carbs_percent',      color: '#ffb347' },
    { label: 'Fat',       key: 'fat_percent',        color: '#3db8ff' },
    { label: 'Fiber',     key: 'fiber_percent',      color: '#a78bfa' },
    { label: 'Sodium',    key: 'sodium_percent',     color: '#94a3b8' },
  ];

  $('dailyValues').innerHTML = `
    <div style="font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-dim);margin-bottom:12px;">% Daily Value (2000 kcal diet)</div>
    ${dvItems.map(item => {
      const pct = Math.min(breakdown[item.key] || 0, 100);
      return `
        <div class="dv-row">
          <span class="dv-label">${item.label}</span>
          <div class="dv-bar-wrap">
            <div class="dv-bar" style="width:0%;background:${item.color};transition:width 1s ease;" data-target="${pct}"></div>
          </div>
          <span class="dv-pct">${(breakdown[item.key] || 0).toFixed(0)}%</span>
        </div>`;
    }).join('')}`;

  // Animate bars
  setTimeout(() => {
    $('dailyValues').querySelectorAll('.dv-bar').forEach(bar => {
      bar.style.width = `${bar.dataset.target}%`;
    });
  }, 200);
}

function renderRisks(risks) {
  const card = $('risksCard');
  if (!risks.length) { card.style.display = 'none'; return; }

  card.style.display = 'block';
  $('risksList').innerHTML = risks.map(r => `
    <div class="risk-item level-${r.level}">
      <span class="risk-icon">${r.icon || '⚠️'}</span>
      <div class="risk-body">
        <div class="risk-name">${r.risk}</div>
        <div class="risk-reason">${r.reason}${r.personalized ? ' <em>(Personalized)</em>' : ''}</div>
      </div>
      <span class="risk-level">${r.level}</span>
    </div>`).join('');
}

function renderRecTab(recs) {
  if (!recs) return;
  const content = $('recContent');
  const tabMap = {
    tips:         recs.general_tips || [],
    alternatives: recs.healthier_alternatives || [],
    lifestyle:    recs.lifestyle_tips || [],
    pairing:      recs.meal_pairing || [],
  };

  const items = tabMap[state.currentRecTab] || [];
  content.innerHTML = `<div class="rec-list">${
    items.map(tip => `
      <div class="rec-item">
        <span>${tip}</span>
      </div>`).join('') || '<div class="rec-item">No recommendations available.</div>'
  }</div>`;

  // Portion advice
  const pa = $('portionAdvice');
  if (recs.portion_advice) {
    pa.textContent = `📏 ${recs.portion_advice}`;
    pa.style.display = 'block';
  } else {
    pa.style.display = 'none';
  }
}

function renderPredictions(predictions) {
  $('predictionsList').innerHTML = predictions.map((p, i) => `
    <div class="prediction-item">
      <span class="pred-rank">${i + 1}</span>
      <span class="pred-name">${p.food}</span>
      <div class="pred-bar-wrap">
        <div class="pred-bar" style="width:${(p.confidence * 100).toFixed(1)}%"></div>
      </div>
      <span class="pred-pct">${(p.confidence * 100).toFixed(1)}%</span>
    </div>`).join('');
}

// ─── Loading States ───────────────────────────────────────────────────────────
const loadingSteps = ['step1', 'step2', 'step3', 'step4'];
let loadingInterval = null;
let stepIndex = 0;

function showLoading(message) {
  loadingCard.style.display = 'block';
  resultsSection.style.display = 'none';
  $('loadingText').textContent = message;
  loadingCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

  // Reset steps
  loadingSteps.forEach(s => { $(s).classList.remove('active', 'done'); });
  $('step1').classList.add('active');
  stepIndex = 0;

  loadingInterval = setInterval(() => {
    if (stepIndex < loadingSteps.length - 1) {
      $(loadingSteps[stepIndex]).classList.remove('active');
      $(loadingSteps[stepIndex]).classList.add('done');
      stepIndex++;
      $(loadingSteps[stepIndex]).classList.add('active');
    }
  }, 800);
}

function hideLoading() {
  clearInterval(loadingInterval);
  loadingCard.style.display = 'none';
}

// ─── History ──────────────────────────────────────────────────────────────────
function addToLocalHistory(data) {
  const entry = {
    food_name: data.food_name,
    calories: data.nutrition?.calories || 0,
    health_score: data.health_score?.score || 0,
    health_label: data.health_score?.label || 'Unknown',
    timestamp: data.timestamp || new Date().toISOString(),
  };
  state.history.unshift(entry);
  if (state.history.length > 50) state.history = state.history.slice(0, 50);
  localStorage.setItem('nutriscan_history', JSON.stringify(state.history));
}

function showHistory() {
  const card = $('historyCard');
  card.style.display = 'block';
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const history = state.history;

  // Summary stats
  if (history.length) {
    const totalCal = history.reduce((s, h) => s + (h.calories || 0), 0);
    const avgScore = history.reduce((s, h) => s + (h.health_score || 0), 0) / history.length;
    $('historySummary').innerHTML = `
      <div class="sum-stat"><div class="sum-num">${history.length}</div><div class="sum-label">Logged Meals</div></div>
      <div class="sum-stat"><div class="sum-num">${Math.round(totalCal)}</div><div class="sum-label">Total Calories</div></div>
      <div class="sum-stat"><div class="sum-num">${avgScore.toFixed(0)}</div><div class="sum-label">Avg Health Score</div></div>
    `;
  } else {
    $('historySummary').innerHTML = '<p style="color:var(--text-muted);font-size:.9rem;">No history yet — analyze some food!</p>';
  }

  // History list
  $('historyList').innerHTML = history.length
    ? history.map(h => `
        <div class="history-item">
          <span class="h-food">${getFoodEmoji(h.food_name)} ${h.food_name}</span>
          <span class="h-cal">${Math.round(h.calories)} kcal</span>
          <span class="h-label ${h.health_label}">${h.health_label}</span>
          <span class="h-date">${formatDate(h.timestamp)}</span>
        </div>`).join('')
    : '<p style="color:var(--text-muted);font-size:.9rem;text-align:center;padding:20px;">No entries yet</p>';

  // Also try to fetch from API
  fetchHistory();
}

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/history?user_id=${state.userId}&limit=20`);
    if (res.ok) {
      const data = await res.json();
      if (data.history?.length) {
        state.history = data.history.map(h => ({
          food_name: h.food_name,
          calories: h.calories,
          health_score: h.health_score,
          health_label: h.health_label,
          timestamp: h.timestamp,
        }));
        localStorage.setItem('nutriscan_history', JSON.stringify(state.history));
      }
    }
  } catch (e) { /* use local history */ }
}

function hideHistory() {
  $('historyCard').style.display = 'none';
}

function saveToLog() {
  if (!state.currentResult) return;
  addToLocalHistory(state.currentResult);
  showToast('✅ Saved to your food log!');
}

// ─── Profile ──────────────────────────────────────────────────────────────────
function setupProfile() {
  $('btnProfile').addEventListener('click', () => {
    $('profileModal').style.display = 'flex';
  });
}

function closeProfile() {
  $('profileModal').style.display = 'none';
}

function loadProfileFromStorage() {
  const p = state.profile;
  if (!p) return;
  if (p.age) $('profileAge').value = p.age;
  if (p.gender) $('profileGender').value = p.gender;
  if (p.weight_kg) $('profileWeight').value = p.weight_kg;
  if (p.height_cm) $('profileHeight').value = p.height_cm;
  if (p.goal) $('profileGoal').value = p.goal;
  if (p.health_conditions) $('profileConditions').value =
    Array.isArray(p.health_conditions) ? p.health_conditions.join(', ') : p.health_conditions;
  if (p.dietary_preferences) $('profileDiet').value =
    Array.isArray(p.dietary_preferences) ? p.dietary_preferences.join(', ') : p.dietary_preferences;
}

async function saveProfile() {
  const profile = {
    user_id: state.userId,
    age: parseInt($('profileAge').value) || null,
    gender: $('profileGender').value || null,
    weight_kg: parseFloat($('profileWeight').value) || null,
    height_cm: parseFloat($('profileHeight').value) || null,
    goal: $('profileGoal').value || null,
    health_conditions: $('profileConditions').value.split(',').map(s => s.trim()).filter(Boolean),
    dietary_preferences: $('profileDiet').value.split(',').map(s => s.trim()).filter(Boolean),
  };

  state.profile = profile;
  localStorage.setItem('nutriscan_profile', JSON.stringify(profile));

  // Try saving to API
  try {
    await fetch(`${API_BASE}/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
  } catch (e) { /* saved locally */ }

  closeProfile();
  showToast('✅ Profile saved! Future analyses will be personalized.');
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function resetAnalysis() {
  clearImage();
  foodNameInput.value = '';
  ingredientsInput.value = '';
  portionInput.value = 100;
  resultsSection.style.display = 'none';
  $('historyCard').style.display = 'none';
  state.currentResult = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showToast(msg, duration = 3000) {
  const toast = $('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

function formatDate(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffH = diffMs / 3600000;
  if (diffH < 1) return 'Just now';
  if (diffH < 24) return `${Math.floor(diffH)}h ago`;
  if (diffH < 48) return 'Yesterday';
  return d.toLocaleDateString();
}

function getFoodEmoji(name) {
  if (!name) return '🍽️';
  const n = name.toLowerCase();
  const map = {
    pizza: '🍕', burger: '🍔', sushi: '🍱', salad: '🥗', pasta: '🍝',
    steak: '🥩', chicken: '🍗', ramen: '🍜', tacos: '🌮', cake: '🎂',
    "ice cream": '🍦', donut: '🍩', waffle: '🧇', pancake: '🥞',
    soup: '🍲', sandwich: '🥪', fish: '🐟', salmon: '🐟', shrimp: '🍤',
    rice: '🍚', noodle: '🍜', egg: '🍳', cheese: '🧀', bread: '🍞',
    apple: '🍎', banana: '🍌', fruit: '🍓', cookie: '🍪', chocolate: '🍫',
    coffee: '☕', tea: '🍵', beer: '🍺', wine: '🍷',
  };
  for (const [key, emoji] of Object.entries(map)) {
    if (n.includes(key)) return emoji;
  }
  return '🍽️';
}

// Close profile modal on overlay click
$('profileModal').addEventListener('click', e => {
  if (e.target === $('profileModal')) closeProfile();
});

// Expose to HTML onclick attributes
window.resetAnalysis = resetAnalysis;
window.showHistory   = showHistory;
window.hideHistory   = hideHistory;
window.saveToLog     = saveToLog;
window.closeProfile  = closeProfile;
window.saveProfile   = saveProfile;
window.selectFood    = selectFood;
