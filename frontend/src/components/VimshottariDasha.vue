<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="px-5 py-4 border-b border-gray-100 flex items-start justify-between gap-4">
      <div>
        <h4 class="font-bold text-gray-800">Vimshottari Dasha</h4>
        <div v-if="personName" class="text-xs text-gray-500 mt-0.5">
          For: <span class="font-semibold text-gray-700">{{ personName }}</span>
        </div>
        <div class="text-xs text-gray-500">
          <span v-if="activeTab === 'maha'">Mahadasha</span>
          <span v-else-if="activeTab === 'antar'">Antardasha • {{ selectedMaha?.planet || '—' }}</span>
          <span v-else-if="activeTab === 'praty'">Pratyantardasha • {{ selectedMaha?.planet || '—' }} / {{ selectedAntar?.planet || '—' }}</span>
          <span v-else>Sookshmadasha • {{ selectedMaha?.planet || '—' }} / {{ selectedAntar?.planet || '—' }} / {{ selectedPraty?.planet || '—' }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="activeTab !== 'maha'"
          @click="goBack()"
          class="text-xs bg-gray-50 border border-gray-200 text-gray-700 px-3 py-2 rounded-lg font-semibold hover:bg-gray-100 transition"
        >
          ← Back
        </button>
      </div>
    </div>

    <div class="px-5 py-4 border-b border-gray-100">
      <div class="flex flex-wrap items-center gap-2">
        <button
          class="text-xs px-3 py-2 rounded-full font-bold border transition"
          :class="activeTab === 'maha' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'"
          @click="setTab('maha')"
        >
          1 Mahadasha
        </button>
        <button
          class="text-xs px-3 py-2 rounded-full font-bold border transition"
          :disabled="!selectedMaha"
          :class="activeTab === 'antar' ? 'bg-indigo-600 text-white border-indigo-600' : (!selectedMaha ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50')"
          @click="selectedMaha && setTab('antar')"
        >
          2 Antardasha
        </button>
        <button
          class="text-xs px-3 py-2 rounded-full font-bold border transition"
          :disabled="!selectedAntar"
          :class="activeTab === 'praty' ? 'bg-indigo-600 text-white border-indigo-600' : (!selectedAntar ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50')"
          @click="selectedAntar && setTab('praty')"
        >
          3 Pratyantardasha
        </button>
        <button
          class="text-xs px-3 py-2 rounded-full font-bold border transition"
          :disabled="!selectedPraty"
          :class="activeTab === 'sook' ? 'bg-indigo-600 text-white border-indigo-600' : (!selectedPraty ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50')"
          @click="selectedPraty && setTab('sook')"
        >
          4 Sookshmadasha
        </button>
      </div>
    </div>

    <div v-if="currentRows.length === 0" class="p-5 text-sm text-gray-500">
      No dasha data available.
    </div>

    <div v-else class="overflow-x-auto">
      <table class="min-w-[720px] w-full text-sm">
        <thead class="bg-gray-50">
          <tr class="text-left text-gray-600">
            <th class="px-4 py-3 font-semibold">Planet</th>
            <th class="px-4 py-3 font-semibold">Start Date</th>
            <th class="px-4 py-3 font-semibold">End Date</th>
            <th class="px-4 py-3 font-semibold">Years</th>
            <th class="px-4 py-3 font-semibold w-10"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in currentRows"
            :key="row.key"
            class="border-t border-gray-100 hover:bg-gray-50/60 transition"
          >
            <td class="px-4 py-3 font-semibold text-gray-900">{{ _displayPlanet(row.planet) }}</td>
            <td class="px-4 py-3 text-gray-800">{{ _fmtStartLabel(row) }}</td>
            <td class="px-4 py-3 text-gray-800">{{ _fmtDate(row.endDate) }}</td>
            <td class="px-4 py-3 text-gray-700">{{ row.years }}</td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="row.canExpand && activeTab !== 'sook'"
                @click="expand(row)"
                class="p-2 rounded-lg hover:bg-indigo-50 text-gray-400 hover:text-indigo-700 transition"
                :disabled="loading"
                title="Open next level"
              >
                <span class="text-lg leading-none">›</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="error" class="px-5 py-4 text-sm text-red-600 border-t border-gray-100">
        {{ error }}
      </div>
      <div v-if="loading" class="px-5 py-4 text-sm text-gray-500 border-t border-gray-100">
        Loading…
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import axios from 'axios';

const props = defineProps({
  dasha: { type: Array, default: () => [] },
  personName: { type: String, default: '' },
});

const API_BASE = 'http://localhost:8000';

const activeTab = ref('maha');
const loading = ref(false);
const error = ref('');

const selectedMaha = ref(null);
const selectedAntar = ref(null);
const selectedPraty = ref(null);

const antarRows = ref([]);
const pratyRows = ref([]);
const sookRows = ref([]);

const safeStr = (v) => (v === null || v === undefined || v === '' ? '—' : String(v));
const fmtYears = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(2) : '—';
};

const mahaRows = computed(() => {
  const list = Array.isArray(props.dasha) ? props.dasha : [];
  return list.map((d, idx) => ({
    key: `${safeStr(d?.planet)}-${idx}`,
    planet: safeStr(d?.planet),
    startLabel: safeStr(d?.start_label || d?.start_date),
    startDate: safeStr(d?.start_date),
    endDate: safeStr(d?.end_date),
    years: fmtYears(d?.years),
    totalYears: Number(d?.total_years ?? d?.years) || 0,
    offsetYears: Number(d?.offset_years ?? 0) || 0,
    canExpand: true,
  }));
});

const currentRows = computed(() => {
  if (activeTab.value === 'maha') return mahaRows.value;
  if (activeTab.value === 'antar') return antarRows.value;
  if (activeTab.value === 'praty') return pratyRows.value;
  return sookRows.value;
});

const setTab = (t) => {
  error.value = '';

  // Reset logic when user navigates "up" levels via tabs.
  // Goal: once you go back to a higher level, you cannot jump forward again
  // unless you expand a row again.
  if (t === 'maha') {
    // Back to top: clear everything.
    selectedMaha.value = null;
    selectedAntar.value = null;
    selectedPraty.value = null;
    antarRows.value = [];
    pratyRows.value = [];
    sookRows.value = [];
  } else if (t === 'antar') {
    // Keep Mahadasha selection + cached antar list, but clear deeper state.
    selectedAntar.value = null;
    selectedPraty.value = null;
    pratyRows.value = [];
    sookRows.value = [];
  } else if (t === 'praty') {
    // Keep Praty rows list, but clear Sookshma state.
    selectedPraty.value = null;
    sookRows.value = [];
  }

  activeTab.value = t;
};

const goBack = () => {
  if (activeTab.value === 'sook') {
    setTab('praty');
    return;
  }
  if (activeTab.value === 'praty') {
    setTab('antar');
    return;
  }
  if (activeTab.value === 'antar') {
    // Going back to Mahadasha should reset drill-down state.
    setTab('maha');
  }
};

const _mapSubRows = (list) => {
  const arr = Array.isArray(list) ? list : [];
  return arr.map((d, idx) => ({
    key: `${safeStr(d?.planet)}-${safeStr(d?.start_date)}-${idx}`,
    planet: safeStr(d?.planet),
    startLabel: safeStr(d?.start_date),
    startDate: safeStr(d?.start_date),
    endDate: safeStr(d?.end_date),
    years: fmtYears(d?.years),
    totalYears: Number(d?.total_years ?? d?.years) || 0,
    offsetYears: Number(d?.offset_years ?? 0) || 0,
    canExpand: true,
  }));
};

const _fetchSubperiods = async (parentRow) => {
  const payload = {
    parent_planet: parentRow.planet,
    start_date: parentRow.startDate,
    end_date: parentRow.endDate,
    parent_total_years: parentRow.totalYears,
    offset_years: parentRow.offsetYears,
  };
  const res = await axios.post(`${API_BASE}/dasha/subperiods`, payload);
  return _mapSubRows(res.data);
};

const _abbr = (name) => {
  const n = String(name || '').trim();
  const map = {
    Sun: 'SU',
    Moon: 'MO',
    Mars: 'MA',
    Mercury: 'ME',
    Jupiter: 'JU',
    Venus: 'VE',
    Saturn: 'SA',
    Rahu: 'RA',
    Ketu: 'KE',
  };
  return map[n] || (n ? n.slice(0, 2).toUpperCase() : '');
};

const _displayPlanet = (rowPlanet) => {
  if (activeTab.value === 'maha') return rowPlanet;
  if (activeTab.value === 'antar') return `${_abbr(selectedMaha.value?.planet)}-${_abbr(rowPlanet)}`;
  if (activeTab.value === 'praty') return `${_abbr(selectedMaha.value?.planet)}-${_abbr(selectedAntar.value?.planet)}-${_abbr(rowPlanet)}`;
  return `${_abbr(selectedMaha.value?.planet)}-${_abbr(selectedAntar.value?.planet)}-${_abbr(selectedPraty.value?.planet)}-${_abbr(rowPlanet)}`;
};

const _fmtDate = (iso) => {
  const s = String(iso || '').trim();
  if (!s || s === '—') return '—';
  const dt = new Date(`${s}T00:00:00`);
  if (Number.isNaN(dt.getTime())) return s;
  const parts = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).formatToParts(dt);
  const day = parts.find(p => p.type === 'day')?.value;
  const mon = parts.find(p => p.type === 'month')?.value;
  const yr = parts.find(p => p.type === 'year')?.value;
  return day && mon && yr ? `${day}-${mon}-${yr}` : s;
};

const _fmtStartLabel = (row) => {
  // Keep "Birth" label when a period starts exactly at birth.
  if (activeTab.value === 'maha') {
    if (row.startLabel === 'Birth') return 'Birth';
    return _fmtDate(row.startDate);
  }
  const parent = activeTab.value === 'antar'
    ? selectedMaha.value
    : activeTab.value === 'praty'
      ? selectedAntar.value
      : selectedPraty.value;
  if (parent?.startLabel === 'Birth' && row.startDate === parent?.startDate) return 'Birth';
  return _fmtDate(row.startDate);
};

const expand = async (row) => {
  if (!row?.startDate || !row?.endDate || !row?.planet) return;
  error.value = '';
  loading.value = true;
  try {
    if (activeTab.value === 'maha') {
      selectedMaha.value = row;
      selectedAntar.value = null;
      selectedPraty.value = null;
      pratyRows.value = [];
      sookRows.value = [];
      antarRows.value = await _fetchSubperiods(row);
      activeTab.value = 'antar';
      return;
    }

    if (activeTab.value === 'antar') {
      selectedAntar.value = row;
      selectedPraty.value = null;
      sookRows.value = [];
      pratyRows.value = await _fetchSubperiods(row);
      activeTab.value = 'praty';
      return;
    }

    if (activeTab.value === 'praty') {
      selectedPraty.value = row;
      sookRows.value = await _fetchSubperiods(row);
      activeTab.value = 'sook';
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || 'Failed to load sub-periods.';
    error.value = String(msg);
  } finally {
    loading.value = false;
  }
};
</script>
