/* LibreCoach Settings UI */

const SETTINGS_FIELDS = [
  'geo_enabled', 'geo_device_tracker_primary', 'geo_device_tracker_secondary',
  'geo_update_threshold', 'victron_enabled', 'microair_enabled',
  'microair_email', 'microair_password', 'ble_scan_interval', 'beta_enabled'
];

const TOGGLE_FIELDS = [
  'geo_enabled', 'victron_enabled', 'microair_enabled', 'beta_enabled'
];

let entityCache = [];

// --- API ---

async function loadSettings() {
  const resp = await fetch('./api/settings');
  if (!resp.ok) throw new Error('Failed to load settings');
  return resp.json();
}

async function saveSettings(settings) {
  const resp = await fetch('./api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
  if (!resp.ok) throw new Error('Failed to save settings');
  return resp.json();
}

async function fetchEntities(domain) {
  const resp = await fetch('./api/entities?domain=' + encodeURIComponent(domain));
  if (!resp.ok) return [];
  return resp.json();
}

// --- Form helpers ---

function populateForm(settings) {
  for (const key of SETTINGS_FIELDS) {
    const el = document.getElementById(key);
    if (!el) continue;
    if (TOGGLE_FIELDS.includes(key)) {
      el.checked = !!settings[key];
    } else if (el.type === 'number') {
      el.value = settings[key] ?? '';
    } else {
      el.value = settings[key] ?? '';
    }
  }
  updateConditionalFields();
}

function collectForm() {
  const settings = {};
  for (const key of SETTINGS_FIELDS) {
    const el = document.getElementById(key);
    if (!el) continue;
    if (TOGGLE_FIELDS.includes(key)) {
      settings[key] = el.checked;
    } else if (el.type === 'number') {
      let val = parseInt(el.value, 10) || 0;
      if (key === 'ble_scan_interval') {
        val = Math.max(10, Math.min(300, val));
      }
      settings[key] = val;
    } else {
      settings[key] = el.value;
    }
  }
  return settings;
}

function updateConditionalFields() {
  const geoFields = document.getElementById('geo-fields');
  const microairFields = document.getElementById('microair-fields');

  if (geoFields) {
    geoFields.classList.toggle('hidden', !document.getElementById('geo_enabled').checked);
  }
  if (microairFields) {
    microairFields.classList.toggle('hidden', !document.getElementById('microair_enabled').checked);
  }
}

function showStatus(msg, type) {
  const el = document.getElementById('save-status');
  el.textContent = msg;
  el.className = 'status-msg ' + type;
  if (type === 'success') {
    setTimeout(() => { el.textContent = ''; }, 3000);
  }
}

// --- Entity picker ---

function setupEntityPicker(inputId, dropdownId) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  if (!input || !dropdown) return;

  input.addEventListener('focus', () => {
    renderDropdown(dropdown, input.value);
    dropdown.classList.add('open');
  });

  input.addEventListener('input', () => {
    renderDropdown(dropdown, input.value);
  });

  input.addEventListener('blur', () => {
    // Delay to allow click on dropdown item
    setTimeout(() => dropdown.classList.remove('open'), 150);
  });

  dropdown.addEventListener('mousedown', (e) => {
    const li = e.target.closest('li');
    if (li && li.dataset.entityId) {
      input.value = li.dataset.entityId;
      dropdown.classList.remove('open');
    }
  });
}

function renderDropdown(dropdown, filter) {
  const query = (filter || '').toLowerCase();
  dropdown.innerHTML = '';

  const matches = entityCache.filter(e =>
    e.entity_id.toLowerCase().includes(query) ||
    e.friendly_name.toLowerCase().includes(query)
  ).slice(0, 50);

  for (const entity of matches) {
    const li = document.createElement('li');
    li.dataset.entityId = entity.entity_id;
    li.innerHTML = escapeHtml(entity.entity_id) +
      '<span class="friendly-name">' + escapeHtml(entity.friendly_name) + '</span>';
    dropdown.appendChild(li);
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// --- Init ---

async function init() {
  // Load settings
  try {
    const settings = await loadSettings();
    const versionEl = document.getElementById('version');
    if (versionEl && settings._version) {
      versionEl.textContent = 'v' + settings._version;
    }
    populateForm(settings);
  } catch (e) {
    showStatus('Failed to load settings', 'error');
  }

  // Load entity list for pickers
  try {
    entityCache = await fetchEntities('device_tracker');
  } catch (e) {
    // Entity picker won't work but form still functions
  }

  // Wire up entity pickers
  setupEntityPicker('geo_device_tracker_primary', 'dropdown-primary');
  setupEntityPicker('geo_device_tracker_secondary', 'dropdown-secondary');

  // Wire up conditional field toggles
  document.getElementById('geo_enabled').addEventListener('change', updateConditionalFields);
  document.getElementById('microair_enabled').addEventListener('change', updateConditionalFields);

  // Wire up save
  document.getElementById('save-btn').addEventListener('click', async () => {
    try {
      const settings = collectForm();
      document.getElementById('save-btn').textContent = 'Saving...';
      await saveSettings(settings);
      showStatus('Settings saved — restart add-on to apply changes', 'success');
    } catch (e) {
      showStatus('Failed to save: ' + e.message, 'error');
    } finally {
      document.getElementById('save-btn').textContent = 'Save Settings';
    }
  });
}

document.addEventListener('DOMContentLoaded', init);
