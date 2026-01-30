<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3 border-b border-gray-100 pb-4">
      <div>
        <h3 class="text-2xl font-bold text-indigo-900">Daily Horoscope</h3>
        <p v-if="personName" class="text-xs text-gray-600 mt-1">
          For: <span class="font-semibold text-gray-800">{{ personName }}</span>
        </p>
        <p class="text-sm text-gray-500">Based on natal Moon and today’s Moon transit (sidereal, Lahiri).</p>
      </div>

      <div class="flex items-center gap-2">
        <input
          v-model="forDate"
          type="date"
          class="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white"
        />
        <button
          type="button"
          @click="fetchHoroscope()"
          class="bg-indigo-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-indigo-700 transition disabled:opacity-50"
          :disabled="loading || !request"
        >
          {{ loading ? 'Loading…' : 'Get' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="p-4 rounded-xl bg-red-50 text-red-700 border border-red-100 text-sm">
      {{ error }}
    </div>

    <div v-if="!request" class="p-4 rounded-xl bg-gray-50 text-gray-600 border border-gray-100 text-sm">
      Please generate a kundli first.
    </div>

    <div v-else-if="loading && !data" class="p-4 rounded-xl bg-gray-50 text-gray-600 border border-gray-100 text-sm">
      Fetching daily horoscope…
    </div>

    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h4 class="text-lg font-bold text-gray-900">Overall</h4>
              <div class="text-xs text-gray-500 mt-1">
                Date: <span class="font-semibold text-gray-700">{{ data.for_date }}</span> • TZ: {{ data.timezone }}
              </div>
            </div>
            <span
              class="px-3 py-1 rounded-full text-xs font-bold border"
              :class="sentimentClass(data.overall?.sentiment)"
            >
              {{ (data.overall?.sentiment || '—').toUpperCase() }} • {{ data.overall?.score ?? '—' }}/100
            </span>
          </div>

          <p class="text-sm text-gray-700 mt-4">
            {{ data.overall?.summary || '—' }}
          </p>

          <ul class="mt-4 space-y-2">
            <li v-for="(h, i) in (data.overall?.highlights || [])" :key="i" class="text-sm text-gray-700">
              • {{ h }}
            </li>
          </ul>
        </div>

        <div v-if="data.breakdown" class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Career • Finance • Love • Health</h4>
          <p class="text-xs text-gray-500 mt-1">
            Based on Moon transit (House {{ data.breakdown?.basis?.moon_house_from_natal_moon ?? '—' }} from natal Moon).
          </p>

          <div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="flex items-start justify-between gap-2">
                <div class="font-bold text-gray-900">Career</div>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold border" :class="sentimentClass(data.breakdown?.career?.sentiment)">
                  {{ (data.breakdown?.career?.sentiment || '—').toUpperCase() }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">Score: {{ data.breakdown?.career?.score ?? '—' }}/100</div>
              <div class="text-sm text-gray-700 mt-2">{{ data.breakdown?.career?.summary || '—' }}</div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DO</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.career?.do || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DON'T</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.career?.dont || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
            </div>

            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="flex items-start justify-between gap-2">
                <div class="font-bold text-gray-900">Finance</div>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold border" :class="sentimentClass(data.breakdown?.finance?.sentiment)">
                  {{ (data.breakdown?.finance?.sentiment || '—').toUpperCase() }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">Score: {{ data.breakdown?.finance?.score ?? '—' }}/100</div>
              <div class="text-sm text-gray-700 mt-2">{{ data.breakdown?.finance?.summary || '—' }}</div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DO</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.finance?.do || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DON'T</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.finance?.dont || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
            </div>

            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="flex items-start justify-between gap-2">
                <div class="font-bold text-gray-900">Love</div>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold border" :class="sentimentClass(data.breakdown?.love?.sentiment)">
                  {{ (data.breakdown?.love?.sentiment || '—').toUpperCase() }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">Score: {{ data.breakdown?.love?.score ?? '—' }}/100</div>
              <div class="text-sm text-gray-700 mt-2">{{ data.breakdown?.love?.summary || '—' }}</div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DO</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.love?.do || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DON'T</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.love?.dont || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
            </div>

            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="flex items-start justify-between gap-2">
                <div class="font-bold text-gray-900">Health</div>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold border" :class="sentimentClass(data.breakdown?.health?.sentiment)">
                  {{ (data.breakdown?.health?.sentiment || '—').toUpperCase() }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">Score: {{ data.breakdown?.health?.score ?? '—' }}/100</div>
              <div class="text-sm text-gray-700 mt-2">{{ data.breakdown?.health?.summary || '—' }}</div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DO</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.health?.do || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
              <div class="mt-3">
                <div class="text-[11px] font-bold text-gray-600">DON'T</div>
                <ul class="mt-1 space-y-1">
                  <li v-for="(s, i) in (data.breakdown?.health?.dont || [])" :key="i" class="text-sm text-gray-700">• {{ s }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Remedies</h4>
          <p class="text-xs text-gray-500 mt-1">Shown when a challenge is detected (and also a weekday remedy).</p>

          <div v-if="(data.remedies || []).length === 0" class="text-sm text-gray-600 mt-3">
            No special remedies suggested for today.
          </div>

          <div v-else class="mt-4 space-y-4">
            <div
              v-for="(r, idx) in data.remedies"
              :key="idx"
              class="border border-gray-100 rounded-xl p-4 bg-gray-50"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <div class="font-bold text-gray-900">{{ r.title }}</div>
                  <div v-if="r.why" class="text-xs text-gray-500 mt-0.5">{{ r.why }}</div>
                </div>
                <div class="text-[11px] text-gray-500 whitespace-nowrap">
                  <span class="font-semibold">{{ r.type || 'remedy' }}</span>
                  <span v-if="r.when"> • {{ r.when }}</span>
                </div>
              </div>

              <ul class="mt-3 space-y-1">
                <li v-for="(s, i) in (r.steps || [])" :key="i" class="text-sm text-gray-700">
                  • {{ s }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Moon Snapshot</h4>
          <div class="mt-3 text-sm text-gray-700 space-y-2">
            <div>
              <div class="text-xs text-gray-500">Natal Moon</div>
              <div class="font-semibold">{{ data.natal?.moon_sign || '—' }} • {{ data.natal?.moon_nakshatra || '—' }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-500">Transit Moon</div>
              <div class="font-semibold">
                {{ data.transit?.moon_sign || '—' }} • {{ data.transit?.moon_nakshatra || '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">
                From natal Moon: House {{ data.transit?.moon_house_from_natal_moon ?? '—' }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="(data.problems || []).length" class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Challenges Detected</h4>
          <ul class="mt-3 space-y-3">
            <li v-for="(p, i) in data.problems" :key="i" class="text-sm text-gray-700">
              <div class="font-semibold">{{ p.title }}</div>
              <div class="text-xs text-gray-500 mt-0.5">{{ p.detail }}</div>
            </li>
          </ul>
        </div>

        <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4 text-xs text-indigo-900">
          <div class="font-semibold">Note</div>
          <div class="mt-1">{{ data.disclaimer }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import api from '../api/client'

const props = defineProps({
  request: { type: Object, default: null },
  personName: { type: String, default: '' },
})

const loading = ref(false)
const error = ref('')
const data = ref(null)

const todayIso = () => {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const forDate = ref(todayIso())

const sentimentClass = (s) => {
  if (s === 'good') return 'bg-green-50 text-green-700 border-green-200'
  if (s === 'challenging') return 'bg-red-50 text-red-700 border-red-200'
  return 'bg-amber-50 text-amber-700 border-amber-200'
}

const fetchHoroscope = async () => {
  if (!props.request) return
  loading.value = true
  error.value = ''
  try {
    const payload = { ...props.request, for_date: forDate.value }
    const res = await api.post('/horoscope/daily', payload)
    data.value = res.data
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || 'Failed to load daily horoscope.'
    error.value = String(msg)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.request,
  (nv) => {
    if (nv) fetchHoroscope()
  },
  { immediate: true }
)

onMounted(() => {
  if (props.request) fetchHoroscope()
})
</script>
