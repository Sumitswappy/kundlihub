<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3 border-b border-gray-100 pb-4">
      <div>
        <h3 class="text-2xl font-bold text-indigo-900">Shani Sade Sati</h3>
        <p v-if="personName" class="text-xs text-gray-600 mt-1">
          For: <span class="font-semibold text-gray-800">{{ personName }}</span>
        </p>
        <p class="text-sm text-gray-500">Based on natal Moon sign and Saturn sidereal transit (Lahiri).</p>
      </div>

      <div class="flex items-center gap-2">
        <input
          v-model="forDate"
          type="date"
          class="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white"
        />
        <button
          type="button"
          @click="fetchSadeSati()"
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
      Fetching Sade Sati period chart…
    </div>

    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h4 class="text-lg font-bold text-gray-900">Status</h4>
              <div class="text-xs text-gray-500 mt-1">
                Date: <span class="font-semibold text-gray-700">{{ data.for_date }}</span> • TZ: {{ data.timezone }}
              </div>
            </div>
            <span
              class="px-3 py-1 rounded-full text-xs font-bold border"
              :class="statusClass(data.status?.is_active, data.status?.current_severity)"
            >
              <template v-if="data.status?.is_active">
                ACTIVE • {{ (data.status?.current_phase || '—').toUpperCase() }}
              </template>
              <template v-else>
                NOT ACTIVE
              </template>
            </span>
          </div>

          <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="text-xs text-gray-500">Natal Moon</div>
              <div class="font-bold text-gray-900 mt-1">{{ data.natal?.moon_sign || '—' }}</div>
              <div class="text-xs text-gray-500 mt-1">Rashi: {{ data.natal?.moon_rashi ?? '—' }}</div>
            </div>

            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="text-xs text-gray-500">Saturn (for date)</div>
              <div class="font-bold text-gray-900 mt-1">{{ data.today?.saturn_sign || '—' }}</div>
              <div class="text-xs text-gray-500 mt-1">Rashi: {{ data.today?.saturn_rashi ?? '—' }}</div>
            </div>

            <div class="border border-gray-100 rounded-xl p-4 bg-gray-50">
              <div class="text-xs text-gray-500">Cycle Window (approx)</div>
              <div class="text-sm text-gray-700 mt-1">
                <div>
                  Start: <span class="font-semibold">{{ data.status?.cycle_start || '—' }}</span>
                </div>
                <div class="mt-1">
                  End: <span class="font-semibold">{{ data.status?.cycle_end || '—' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Sade Sati Period Chart</h4>
          <p class="text-xs text-gray-500 mt-1">Three phases computed from Saturn’s sign relative to natal Moon.</p>

          <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              v-for="p in (data.phases || [])"
              :key="p.phase"
              class="border border-gray-100 rounded-xl p-4 bg-gray-50"
            >
              <div class="flex items-start justify-between gap-2">
                <div>
                  <div class="font-bold text-gray-900">{{ p.label }}</div>
                  <div class="text-xs text-gray-500 mt-1">
                    Saturn sign: <span class="font-semibold text-gray-700">{{ p.saturn_target_sign || '—' }}</span>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-bold border" :class="severityClass(p.severity)">
                  {{ (p.severity || '—').toUpperCase() }}
                </span>
              </div>

              <div v-if="(p.segments || []).length === 0" class="text-sm text-gray-600 mt-3">
                No segments found in scan range.
              </div>

              <div v-else class="mt-3 space-y-2">
                <div
                  v-for="(s, idx) in p.segments"
                  :key="idx"
                  class="rounded-lg border border-gray-100 bg-white p-3"
                >
                  <div class="text-sm text-gray-800">
                    <span class="font-semibold">{{ s.start }}</span> → <span class="font-semibold">{{ s.end }}</span>
                  </div>
                  <div class="text-xs text-gray-500 mt-1">
                    {{ s.days }} days • ~{{ s.approx_months }} months
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Remedies</h4>
          <p class="text-xs text-gray-500 mt-1">Gentle, practical suggestions. Not medical advice.</p>

          <div v-if="(data.remedies || []).length === 0" class="text-sm text-gray-600 mt-3">
            No remedies returned.
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
                <li v-for="(step, i) in (r.steps || [])" :key="i" class="text-sm text-gray-700">
                  • {{ step }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-6">
        <div v-if="(data.problems || []).length" class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h4 class="text-lg font-bold text-gray-900">Notes</h4>
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
  try {
    const d = new Date()
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
  } catch {
    return ''
  }
}

const forDate = ref(todayIso())

const fetchSadeSati = async () => {
  error.value = ''
  if (!props.request) {
    error.value = 'Please generate a kundli first.'
    return
  }

  loading.value = true
  try {
    const payload = {
      ...props.request,
      for_date: forDate.value || null,
    }
    const resp = await api.post('/sade-sati', payload)
    data.value = resp.data
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'Failed to fetch Sade Sati data.'
  } finally {
    loading.value = false
  }
}

const severityClass = (severity) => {
  if (severity === 'high') return 'bg-red-50 text-red-700 border-red-100'
  if (severity === 'medium') return 'bg-amber-50 text-amber-700 border-amber-100'
  return 'bg-gray-50 text-gray-600 border-gray-100'
}

const statusClass = (isActive, severity) => {
  if (!isActive) return 'bg-green-50 text-green-700 border-green-100'
  if (severity === 'high') return 'bg-red-50 text-red-700 border-red-100'
  return 'bg-amber-50 text-amber-700 border-amber-100'
}

watch(
  () => props.request,
  (val, oldVal) => {
    if (val && val !== oldVal) {
      data.value = null
      error.value = ''
      fetchSadeSati()
    }
  }
)

onMounted(() => {
  if (props.request) fetchSadeSati()
})
</script>
