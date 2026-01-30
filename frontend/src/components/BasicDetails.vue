<template>
  <div class="w-full space-y-8">
    <div
      v-if="showHeader"
      class="flex items-center justify-between bg-white p-4 rounded-xl shadow-sm border border-gray-100"
    >
      <h2 class="text-2xl font-bold text-indigo-900">Astrological Report</h2>
      <button
        @click="$emit('reset')"
        class="bg-indigo-50 text-indigo-700 px-4 py-2 rounded-lg font-semibold hover:bg-indigo-100 transition"
      >
        ← Generate Another
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="space-y-8">
        <div class="bg-white p-6 rounded-xl shadow-md border-t-4 border-indigo-500">
          <h3 class="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <span>📅</span> Birth Details
          </h3>
          <table class="w-full text-sm">
            <tr v-for="(val, label) in birthDetailsMap" :key="label" class="border-b last:border-0">
              <th class="py-3 text-gray-500 font-medium w-1/3">{{ label }}</th>
              <td class="py-3 text-gray-900 font-semibold text-right">{{ val }}</td>
            </tr>
          </table>
        </div>

        <div class="bg-white p-6 rounded-xl shadow-md border-t-4 border-indigo-500">
          <h3 class="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <span>🕉️</span> Panchang Details
          </h3>
          <table class="w-full text-sm">
            <tr v-for="(val, label) in panchangDetailsMap" :key="label" class="border-b last:border-0">
              <th class="py-3 text-gray-500 font-medium">{{ label }}</th>
              <td class="py-3 text-gray-900 font-semibold text-right">{{ val }}</td>
            </tr>
          </table>
        </div>
      </div>

      <div class="bg-white p-6 rounded-xl shadow-md border-t-4 border-indigo-500 h-fit">
        <h3 class="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
          <span>✨</span> Avakhada Details
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8">
          <table class="w-full text-sm">
            <tr v-for="(val, label) in avakhadaLeft" :key="label" class="border-b last:border-0">
              <th class="py-3 text-gray-500 font-medium text-left">{{ label }}</th>
              <td class="py-3 text-gray-900 font-semibold text-right">{{ val }}</td>
            </tr>
          </table>
          <table class="w-full text-sm">
            <tr v-for="(val, label) in avakhadaRight" :key="label" class="border-b last:border-0 md:border-b">
              <th class="py-3 text-gray-500 font-medium text-left">{{ label }}</th>
              <td class="py-3 text-gray-900 font-semibold text-right">{{ val }}</td>
            </tr>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  kundli: { type: Object, default: null },
  request: { type: Object, default: null },
  showHeader: { type: Boolean, default: true }
});

defineEmits(['reset']);

// Helpers
const fmtNum = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(2) : '—';
};

const d = computed(() => props.kundli || {});
const p = computed(() => d.value.panchang || {});
const a = computed(() => d.value.avakhada || {}); // Assuming backend sends this key

const birthDetailsMap = computed(() => ({
  "Name": props.request?.full_name || '—',
  "Gender": props.request?.gender || d.value?.gender || '—',
  "Date": props.request?.dob || '—',
  "Time": props.request?.tob || '—',
  "Place": props.request?.place || '—',
  "Latitude": fmtNum(p.value.lat ?? props.request?.lat),
  "Longitude": fmtNum(p.value.lon ?? props.request?.lon),
  "Timezone": p.value.tz || 'GMT+5.5',
  "Sunrise": p.value.sunrise || '—',
  "Sunset": p.value.sunset || '—',
  "Ayanamsha": fmtNum(p.value.ayanamsha)
}));

const panchangDetailsMap = computed(() => ({
  "Tithi": p.value.tithi || '—',
  "Karan": p.value.karan || '—',
  "Yog": p.value.yog || '—',
  "Nakshatra": p.value.nakshatra || '—'
}));

const avakhadaLeft = computed(() => ({
  "Varna": a.value.varna || '—',
  "Vashya": a.value.vashya || '—',
  "Yoni": a.value.yoni || '—',
  "Gan": a.value.gan || '—',
  "Nadi": a.value.nadi || '—',
  "Sign": a.value.sign || '—'
}));

const avakhadaRight = computed(() => ({
  "Sign Lord": a.value.sign_lord || '—',
  "Nakshatra-Charan": a.value.nakshatra_charan || '—',
  "Yog": a.value.yog || '—',
  "Karan": a.value.karan || '—',
  "Tithi": a.value.tithi || '—',
  "Paya (Nakshatra)": a.value.paya_nakshatra || a.value.paya || '—',
  "Paya (Moon House)": a.value.paya_moon_house
    ? `${a.value.paya_moon_house}${a.value.moon_house ? ` (House ${a.value.moon_house})` : ''}`
    : '—'
}));
</script>