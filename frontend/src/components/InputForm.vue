<template>
  <div class="max-w-[1400px] mx-auto mt-4 sm:mt-6 px-4 sm:px-6 pb-10">
    <div class="grid grid-cols-12 gap-6 sm:gap-8 lg:gap-12 items-start">

      <div class="col-span-12 lg:col-span-7 flex flex-col">
        
        
        <div class="w-full max-w-3xl mx-auto flex flex-col p-5 sm:p-8 md:p-10 bg-white shadow-2xl rounded-3xl border border-gray-100 h-auto">
          <div class="text-center mb-8">
            
            <h2 class="text-3xl font-extrabold text-gray-900">New Kundli</h2>
            <p class="text-gray-500 mt-2 text-base">Enter birth details to generate your Vedic Chart</p>
          </div>

          <form @submit.prevent="handleSubmit" class="flex flex-col">
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-bold text-gray-700 mb-1.5">Full Name</label>
                <input v-model="form.full_name" type="text" placeholder="E.g. Firstname Lastname"
                  class="w-full px-5 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition text-base" required />
                <p v-if="touched.full_name && errors.full_name" class="mt-1 text-xs font-semibold text-red-600">
                  {{ errors.full_name }}
                </p>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-bold text-gray-700 mb-1.5">Date of Birth</label>
                  <input v-model="form.dob" type="date"
                    class="w-full px-5 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition text-base" required />
                  <p v-if="touched.dob && errors.dob" class="mt-1 text-xs font-semibold text-red-600">
                    {{ errors.dob }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-bold text-gray-700 mb-1.5">Time of Birth</label>
                  <input v-model="form.tob" type="time"
                    class="w-full px-5 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition text-base" required />
                  <p v-if="touched.tob && errors.tob" class="mt-1 text-xs font-semibold text-red-600">
                    {{ errors.tob }}
                  </p>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-bold text-gray-700 mb-1.5">Gender</label>
                  <select v-model="form.gender"
                    class="w-full px-5 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition bg-white text-base" required>
                    <option value="" disabled>Select gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                  <p v-if="touched.gender && errors.gender" class="mt-1 text-xs font-semibold text-red-600">
                    {{ errors.gender }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-bold text-gray-700 mb-1.5">Place of Birth</label>
                  <input v-model="form.place" type="text" placeholder="City, State, Country"
                    class="w-full px-5 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition text-base" required />
                  <p v-if="touched.place && errors.place" class="mt-1 text-xs font-semibold text-red-600">
                    {{ errors.place }}
                  </p>
                </div>
              </div>
            </div>

            <div class="pt-6">
              <button type="submit" :disabled="loading"
                class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 rounded-xl shadow-lg transform transition active:scale-[0.98] disabled:opacity-50 text-lg">
                <span v-if="loading">Calculating...</span>
                <span v-else>Generate Kundli</span>
              </button>
              <p v-if="message" :class="isError ? 'text-red-500' : 'text-green-500'" class="text-center text-sm font-bold mt-4">
                {{ message }}
              </p>
            </div>
          </form>
        </div>
      </div>

      <div class="col-span-12 lg:col-span-5 flex flex-col lg:sticky lg:top-6">
        <div
          v-if="isLoggedIn"
          class="flex flex-col p-5 sm:p-6 bg-white shadow-xl rounded-3xl border border-gray-100 max-h-none lg:max-h-[calc(100vh-140px)]"
        >
           
          <div class="flex items-center justify-between mb-6">
            
            <h4 class="font-bold text-gray-700 text-lg">Saved Kundlis</h4>
            <button @click="fetchHistory" :disabled="historyFetching"
              class="text-xs bg-indigo-50 text-indigo-700 px-4 py-2 rounded-xl font-bold hover:bg-indigo-100 transition inline-flex items-center gap-2">
              <svg v-if="historyLoading" class="animate-spin h-3 w-3" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ historyLoading ? 'Refreshing' : 'Refresh' }}
            </button>
          </div>

          <div class="mb-6">
            <div class="relative">
              <input v-model="searchQuery" type="text" placeholder="Search by name..."
                class="w-full pl-10 pr-4 py-3 text-sm border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-indigo-400 bg-gray-50 transition" />
              <svg class="absolute left-3.5 top-3.5 h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 110-15 7.5 7.5 0 010 15z" />
              </svg>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            <div v-if="filteredHistory.length === 0 && !historyLoading" class="text-center py-10 text-gray-400 text-sm italic">
              No saved records found.
            </div>

            <div class="space-y-4">
              <div v-for="item in filteredHistory" :key="item.id"
                class="bg-gray-50/50 border border-gray-100 rounded-2xl p-4 shadow-sm hover:border-indigo-300 hover:shadow-md transition group">
                <div class="font-bold text-gray-800 text-base truncate">{{ item.full_name }}</div>
                <div class="text-[11px] text-gray-500 font-medium uppercase tracking-wider mt-1 mb-4">
                  {{ item.dob }} • {{ item.tob }}
                </div>
                
                <div class="flex flex-wrap sm:flex-nowrap items-center gap-2 sm:gap-3">
                  <button @click="loadFromHistory(item)" 
                    class="flex-1 text-xs bg-white border border-gray-200 py-2 rounded-lg font-bold text-gray-700 hover:bg-gray-100 transition shadow-sm">
                    Edit
                  </button>
                  <button @click="viewHistoryItem(item)" 
                    class="flex-1 text-xs bg-indigo-600 text-white py-2 rounded-lg font-bold hover:bg-indigo-700 transition shadow-sm">
                    View
                  </button>
                  <button @click="deleteHistoryItem(item.id)" 
                    class="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition">
                    <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="p-5 sm:p-6 bg-white shadow-xl rounded-3xl border border-gray-100">
          <h4 class="font-bold text-gray-800 text-lg">Saved Kundlis</h4>
          <p class="text-sm text-gray-600 mt-2">
            Login to save your kundlis and access full features.
          </p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import api from '../api/client';
const emit = defineEmits(['submit-success']);

const props = defineProps({
  isLoggedIn: { type: Boolean, default: false },
});

// State
const form = reactive({ full_name: '', gender: '', dob: '', tob: '', place: '', lat: null, lon: null });
const loading = ref(false);
const message = ref('');
const isError = ref(false);
const history = ref([]);
const historyLoading = ref(false);
const historyFetching = ref(false);
const searchQuery = ref('');

const touched = reactive({ full_name: false, gender: false, dob: false, tob: false, place: false });
const errors = reactive({ full_name: '', gender: '', dob: '', tob: '', place: '' });

const _trimOrEmpty = (v) => (v == null ? '' : String(v)).trim();

const normalizeDob = (dob) => {
  const s = _trimOrEmpty(dob);
  if (!s) return '';
  // Accept YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  // Accept DD-MM-YYYY or DD/MM/YYYY
  const m = s.match(/^(\d{2})[\/-](\d{2})[\/-](\d{4})$/);
  if (m) return `${m[3]}-${m[2]}-${m[1]}`;
  return s;
};

const normalizeTob = (tob) => {
  const s = _trimOrEmpty(tob);
  if (!s) return '';
  const m = s.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return s;
  return `${m[1]}:${m[2]}`;
};

const validateForm = ({ markTouched = false } = {}) => {
  if (markTouched) {
    touched.full_name = true;
    touched.gender = true;
    touched.dob = true;
    touched.tob = true;
    touched.place = true;
  }

  const name = _trimOrEmpty(form.full_name);
  errors.full_name = name.length >= 2 ? '' : 'Please enter your full name.';

  const gender = _trimOrEmpty(form.gender);
  errors.gender = gender ? '' : 'Please select gender.';

  const dobIso = normalizeDob(form.dob);
  errors.dob = /^\d{4}-\d{2}-\d{2}$/.test(dobIso) ? '' : 'Please select a valid date.';

  const tobNorm = normalizeTob(form.tob);
  errors.tob = /^\d{2}:\d{2}$/.test(tobNorm) ? '' : 'Please select a valid time.';

  const place = _trimOrEmpty(form.place);
  errors.place = place.length >= 3 ? '' : 'Please enter place of birth.';

  return !errors.full_name && !errors.gender && !errors.dob && !errors.tob && !errors.place;
};

// Live validation once fields are interacted with.
watch(
  () => ({ ...form }),
  () => {
    if (touched.full_name || touched.gender || touched.dob || touched.tob || touched.place) {
      validateForm();
    }
  },
  { deep: true }
);

// Filtered History
const filteredHistory = computed(() => {
  if (!searchQuery.value) return history.value;
  return history.value.filter(item => 
    item.full_name.toLowerCase().includes(searchQuery.value.toLowerCase())
  );
});

// Methods
const fetchHistory = async ({ silent = false } = {}) => {
  if (historyFetching.value) return;
  historyFetching.value = true;
  if (!silent) historyLoading.value = true;
  try {
    const res = await api.get('/history');
    history.value = Array.isArray(res.data) ? res.data : [];
  } catch (e) {
    console.error("History fetch error:", e);
  } finally {
    historyFetching.value = false;
    if (!silent) historyLoading.value = false;
  }
};

const deleteHistoryItem = async (id) => {
  if (!confirm("Delete this record permanently?")) return;
  try {
    await api.delete(`/history/${id}`);
    history.value = history.value.filter(item => item.id !== id);
    message.value = "Record deleted.";
    isError.value = false;
  } catch (e) {
    message.value = "Failed to delete.";
    isError.value = true;
  }
};

const loadFromHistory = (item) => {
  Object.assign(form, {
    full_name: item.full_name,
    gender: item.gender || '',
    dob: item.dob,
    tob: item.tob,
    place: item.place
  });
  // Smooth scroll to form top
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const generateFromHistory = async (item) => {
  loading.value = true;
  try {
    const payload = { ...item, lat: null, lon: null };
    const res = await api.post('/generate', payload);
    const recordId = res?.data?.record_id;
    emit('submit-success', { kundli: res.data, request: { ...payload, id: recordId || payload.id } });
  } catch (e) {
    isError.value = true;
    message.value = "Calculation failed.";
  } finally {
    loading.value = false;
  }
};

const viewHistoryItem = async (item) => {
  // IMPORTANT: Do not call /generate here, or it will insert a duplicate record.
  // Prefer saved JSON from /history; if a legacy record is missing avakhada, compute
  // on-demand via /calculate (no DB insert).
  loading.value = true;
  try {
    const request = {
      full_name: item.full_name,
      gender: item.gender || '',
      dob: item.dob,
      tob: item.tob,
      place: item.place,
      lat: null,
      lon: null,
    };

    if (item.avakhada) {
      const kundli = {
        panchang: item.panchang,
        planets: item.planets,
        avakhada: item.avakhada,
        doshas: item.doshas,
        dasha: item.dasha,
      };
      emit('submit-success', { kundli, request: { ...request, id: item.id } });
      return;
    }

    const res = await api.post('/calculate', request);
    emit('submit-success', { kundli: res.data, request: { ...request, id: item.id } });
  } catch (e) {
    isError.value = true;
    message.value = "Failed to load saved record.";
  } finally {
    loading.value = false;
  }
};

const handleSubmit = async () => {
  loading.value = true;
  message.value = '';
  try {
    const ok = validateForm({ markTouched: true });
    if (!ok) {
      isError.value = true;
      message.value = 'Please fix the highlighted fields.';
      return;
    }

    const payload = {
      ...form,
      full_name: _trimOrEmpty(form.full_name),
      gender: _trimOrEmpty(form.gender),
      dob: normalizeDob(form.dob),
      tob: normalizeTob(form.tob),
      place: _trimOrEmpty(form.place),
    };

    const endpoint = props.isLoggedIn ? '/generate' : '/calculate';
    const res = await api.post(endpoint, payload);
    const recordId = res?.data?.record_id;
    emit('submit-success', { kundli: res.data, request: { ...payload, id: recordId || null } });

    if (props.isLoggedIn) {
      await fetchHistory();
    } else {
      message.value = 'Kundli generated (not saved).'
      isError.value = false
    }
  } catch (e) {
    isError.value = true;
    const status = e?.response?.status
    const detail = e?.response?.data?.detail

    if (status === 401) {
      message.value = 'Session expired. Please login again.'
      return
    }

    if (detail) {
      message.value = String(detail)
      return
    }

    message.value = status ? `Server error (${status}).` : 'Server error. Check connection.';
  } finally {
    loading.value = false;
  }
};

const AUTO_REFRESH_MS = 60000;
let refreshIntervalId;

const handleWindowFocus = () => {
  fetchHistory({ silent: true });
};

const handleVisibilityChange = () => {
  if (!document.hidden) fetchHistory({ silent: true });
};

onMounted(() => {
  if (!props.isLoggedIn) return;

  fetchHistory();

  window.addEventListener('focus', handleWindowFocus);
  document.addEventListener('visibilitychange', handleVisibilityChange);

  refreshIntervalId = window.setInterval(() => {
    fetchHistory({ silent: true });
  }, AUTO_REFRESH_MS);
});

onUnmounted(() => {
  if (!props.isLoggedIn) return;

  window.removeEventListener('focus', handleWindowFocus);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
  if (refreshIntervalId) window.clearInterval(refreshIntervalId);
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #ba25fe; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #c195fa; }
</style>