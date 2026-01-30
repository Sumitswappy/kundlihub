<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between border-b border-gray-100 pb-4">
      <div>
        <h3 class="text-2xl font-bold text-indigo-900">Dosha Analysis</h3>
        <p v-if="personName" class="text-xs text-gray-600 mt-1">
          For: <span class="font-semibold text-gray-800">{{ personName }}</span>
        </p>
        <p class="text-sm text-gray-500">Regional calculations including North & South Indian traditions</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-2">
            <div class="p-2 bg-indigo-50 rounded-lg">
              <span class="text-xl">🐍</span>
            </div>
            <div>
              <div class="text-sm font-bold text-gray-800 uppercase tracking-tight">Kalsarpa Dosha</div>
              <div class="text-xs text-gray-400 italic">Longitudinal Nodal Arc Check</div>
            </div>
          </div>
          <span
            class="px-3 py-1 rounded-full text-xs font-bold transition-colors"
            :class="badgeClass(kalsarpaPresent, isPartial)"
          >
            {{ kalsarpaStatusText }}
          </span>
        </div>

        <div class="space-y-4">
          <div v-if="kalsarpaPresent || isPartial">
            <div :class="isPartial ? 'text-amber-600' : 'text-red-600'" class="font-bold flex items-center gap-1">
              <component :is="isPartial ? 'AlertTriangle' : 'Skull'" class="w-4 h-4" />
              {{ isPartial ? 'Partial (Ardh) Kalsarpa' : 'Full Kalsarpa Detected' }}
            </div>
            
            <div v-if="doshas?.kalsarpa?.type" class="mt-2 text-xs bg-gray-50 p-2 rounded border border-gray-100">
              <span class="font-semibold text-gray-700">Type:</span> {{ doshas.kalsarpa.type }} Yoga
            </div>

            <div v-if="isPartial && doshas?.kalsarpa?.outside_planets?.length" class="mt-3">
              <p class="text-xs font-semibold text-gray-500 mb-1 uppercase">Planets outside axis:</p>
              <div class="flex flex-wrap gap-1">
                <span v-for="p in doshas.kalsarpa.outside_planets" :key="p" class="px-2 py-0.5 bg-gray-100 rounded text-[10px] font-medium text-gray-600">
                  {{ p }}
                </span>
              </div>
            </div>
          </div>

          <div v-else-if="kalsarpaPresent === false" class="text-green-600 font-semibold flex items-center gap-1">
            <span class="text-lg">✓</span> No Kalsarpa Yoga found
          </div>

          <div v-else class="text-gray-400 italic">Awaiting calculation data...</div>

          <p class="text-[11px] text-gray-400 leading-relaxed border-t border-gray-50 pt-2">
            Checks if all 7 major planets are hemmed between the Rahu-Ketu longitudinal axis.
          </p>
        </div>
      </div>

      <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-2">
            <div class="p-2 bg-red-50 rounded-lg">
              <span class="text-xl">🔥</span>
            </div>
            <div>
              <div class="text-sm font-bold text-gray-800 uppercase tracking-tight">Manglik (Kuja) Dosha</div>
              <div class="text-xs text-gray-400 italic">Regional Multi-House Rules</div>
            </div>
          </div>
          <span
            class="px-3 py-1 rounded-full text-xs font-bold transition-colors"
            :class="badgeClass(manglikPresent)"
          >
            {{ badgeText(manglikPresent) }}
          </span>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-2 text-[10px] font-bold uppercase tracking-wider mb-2">
            <div class="bg-indigo-50 text-indigo-700 p-2 rounded text-center">
              North: 1, 4, 7, 8, 12
            </div>
            <div class="bg-rose-50 text-rose-700 p-2 rounded text-center">
              South: Incl. 2nd House
            </div>
          </div>

          <div v-if="doshas?.manglik?.cancellation_reasons?.length" class="bg-green-50 border border-green-100 rounded-xl p-3">
            <div class="text-[10px] font-bold text-green-800 uppercase mb-1">Cancellations (Dosha Bhanga)</div>
            <ul class="space-y-1">
              <li v-for="(reason, i) in doshas.manglik.cancellation_reasons" :key="i" class="text-xs text-green-700 flex items-start gap-1">
                <span class="mt-0.5">•</span> {{ reason }}
              </li>
            </ul>
          </div>

          <div class="flex items-center justify-between pt-2 border-t border-gray-50">
            <span class="text-xs font-medium text-gray-500">Mars Placement</span>
            <span class="text-sm font-bold text-gray-900">
              {{ ordinalSuffix(doshas?.manglik?.mars_house) }} House
            </span>
          </div>

          <p class="text-[11px] text-gray-400 leading-relaxed">
            Logic considers Ruchaka Yoga, Jupiter/Saturn aspects, and regional house emphasize.
          </p>
        </div>
      </div>

    </div>

    <div class="rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50 to-white p-4 text-xs text-indigo-900 flex items-start gap-3">
      <span class="text-lg">ℹ️</span>
      <p>
        <strong>Precision Note:</strong> Calculations utilize the high-precision longitudinal nodal arc for Kalsarpa. 
        Manglik status incorporates the 2nd house (Standard South/Keralite) and major cancellations like 
        Jupiter's divine aspect and Ruchaka Yoga.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  doshas: { 
    type: Object, 
    default: () => ({
      kalsarpa: { present: null, is_partial: false, type: '', outside_planets: [], reason: '', note: '' },
      manglik: { present: null, mars_house: 0, cancellation_reasons: [], reason: '', traditions: {} }
    })
  },
  personName: { type: String, default: '' },
})

// Reactivity mapping
const doshas = computed(() => props.doshas || {})
const kalsarpaPresent = computed(() => doshas.value?.kalsarpa?.present ?? null)
const isPartial = computed(() => doshas.value?.kalsarpa?.is_partial ?? false)
const manglikPresent = computed(() => doshas.value?.manglik?.present ?? null)

// Helpers
const kalsarpaStatusText = computed(() => {
  if (kalsarpaPresent.value === true) return 'Full Active'
  if (isPartial.value) return 'Partial (Ardh)'
  if (kalsarpaPresent.value === false) return 'Not Found'
  return 'N/A'
})

const badgeText = (v) => {
  if (v === true) return 'Active'
  if (v === false) return 'Not Found'
  return 'N/A'
}

const badgeClass = (v, partial = false) => {
  if (v === true) return 'bg-red-100 text-red-700 border border-red-200'
  if (partial) return 'bg-amber-100 text-amber-700 border border-amber-200'
  if (v === false) return 'bg-green-100 text-green-700 border border-green-200'
  return 'bg-gray-100 text-gray-500 border border-gray-200'
}

const ordinalSuffix = (h) => {
  const n = parseInt(h)
  if (isNaN(n)) return '—'
  const s = ["th", "st", "nd", "rd"],
        v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}
</script>

<style scoped>
/* Optional: Add custom animations or glassmorphism effects here */
</style>