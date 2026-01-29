<script setup>
import { ref, computed } from 'vue'
import InputForm from './components/InputForm.vue'
import KundliChart from './components/KundliChart.vue'
import PlanetaryPositions from './components/PlanetaryPositions.vue'
import VimshottariDasha from './components/VimshottariDasha.vue'
import BasicDetails from './components/BasicDetails.vue'

// Holds { kundli, request }
const viewModel = ref(null)

const activeTab = ref('chart') // 'chart' | 'positions' | 'dasha' | 'details'

// Function to handle the data emitted from the InputForm
const handleKundliGenerated = (data) => {
  viewModel.value = data
  activeTab.value = 'chart'
}

const reset = () => {
  viewModel.value = null
  activeTab.value = 'chart'
}

const lagnaRashiValue = computed(() => {
  const k = viewModel.value?.kundli
  return k?.panchang?.lagna_rashi ?? k?.panchang?.lagnaRashi ?? null
})

const _mod12 = (n) => ((n % 12) + 12) % 12

const _navamsaStartSign = (rashiNum) => {
  const r = Number(rashiNum)
  if (!Number.isFinite(r)) return null
  // Movable: 1,4,7,10 start from same sign
  if ([1, 4, 7, 10].includes(r)) return r
  // Fixed: 2,5,8,11 start from 9th from sign
  if ([2, 5, 8, 11].includes(r)) return _mod12(r - 1 + 8) + 1
  // Dual: 3,6,9,12 start from 5th from sign
  return _mod12(r - 1 + 4) + 1
}

const _toNavamsa = (rashiNum, degInSign) => {
  const r = Number(rashiNum)
  const deg = Number(degInSign)
  if (!Number.isFinite(r) || !Number.isFinite(deg)) return null

  const partSize = 30 / 9 // 3.333...
  const part = Math.min(8, Math.max(0, Math.floor(deg / partSize)))
  const start = _navamsaStartSign(r)
  if (!start) return null

  const navRashi = _mod12(start - 1 + part) + 1
  const withinPart = deg - part * partSize
  const navDeg = withinPart * 9 // scale to 0..30
  return { rashi: navRashi, deg: navDeg }
}

const navamsaPlanets = computed(() => {
  const planets = viewModel.value?.kundli?.planets
  if (!Array.isArray(planets)) return []
  return planets
    .map((p) => {
      const rashi = Number(p?.rashi)
      const deg = Number(p?.deg ?? (Number.isFinite(Number(p?.lon)) ? (Number(p.lon) % 30) : null))
      const nav = _toNavamsa(rashi, deg)
      if (!nav) return null
      return {
        ...p,
        rashi: nav.rashi,
        deg: Number.isFinite(nav.deg) ? Number(nav.deg.toFixed(2)) : nav.deg,
      }
    })
    .filter(Boolean)
})

const navamsaLagnaRashi = computed(() => {
  const planets = viewModel.value?.kundli?.planets
  if (!Array.isArray(planets)) return null
  const asc = planets.find((p) => String(p?.name) === 'Asc')
  if (!asc) return null
  const rashi = Number(asc?.rashi)
  const deg = Number(asc?.deg ?? (Number.isFinite(Number(asc?.lon)) ? (Number(asc.lon) % 30) : null))
  const nav = _toNavamsa(rashi, deg)
  return nav?.rashi ?? null
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-10">
    <header class="text-center mb-10">
      <h1 class="text-4xl font-bold text-indigo-900">Vedic Kundli Hub</h1>
      <p class="text-gray-600">Precision Astrological Calculations</p>
    </header>

    <main class="container mx-auto px-4">
      <section v-if="!viewModel" class="w-full">
        <InputForm @submit-success="handleKundliGenerated" />
      </section>

      <section v-else class="space-y-10 animate-fade-in">
        <div class="max-w-6xl mx-auto space-y-6">
          <div class="flex items-center justify-between bg-white p-4 rounded-xl shadow-sm border border-gray-100">
            <h2 class="text-2xl font-bold text-indigo-900">Kundli</h2>
            <button
              type="button"
              @click="reset"
              class="bg-indigo-50 text-indigo-700 px-4 py-2 rounded-lg font-semibold hover:bg-indigo-100 transition"
            >
              ← Generate Another
            </button>
          </div>

          <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div class="flex">
              <button
                type="button"
                @click="activeTab = 'chart'"
                class="flex-1 px-4 py-3 text-sm font-semibold transition"
                :class="activeTab === 'chart' ? 'bg-indigo-50 text-indigo-800' : 'bg-white text-gray-600 hover:bg-gray-50'"
              >
                Lagna Chart
              </button>
              <button
                type="button"
                @click="activeTab = 'positions'"
                class="flex-1 px-4 py-3 text-sm font-semibold transition"
                :class="activeTab === 'positions' ? 'bg-indigo-50 text-indigo-800' : 'bg-white text-gray-600 hover:bg-gray-50'"
              >
                Planetary Positions
              </button>
              <button
                type="button"
                @click="activeTab = 'dasha'"
                class="flex-1 px-4 py-3 text-sm font-semibold transition"
                :class="activeTab === 'dasha' ? 'bg-indigo-50 text-indigo-800' : 'bg-white text-gray-600 hover:bg-gray-50'"
              >
                Vimshottari Dasha
              </button>
              <button
                type="button"
                @click="activeTab = 'details'"
                class="flex-1 px-4 py-3 text-sm font-semibold transition"
                :class="activeTab === 'details' ? 'bg-indigo-50 text-indigo-800' : 'bg-white text-gray-600 hover:bg-gray-50'"
              >
                Basic Details
              </button>
            </div>
          </div>

          <div v-if="activeTab === 'chart'" class="bg-white p-6 rounded-xl shadow-md">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
              <div>
                <h3 class="text-xl font-bold mb-4 text-center">Lagna Chart</h3>
                <div class="flex justify-center">
                  <KundliChart
                    :planets="viewModel.kundli?.planets"
                    :lagnaRashi="lagnaRashiValue"
                  />
                </div>
              </div>

              <div>
                <h3 class="text-xl font-bold mb-4 text-center">Navamsa Chart</h3>
                <div class="flex justify-center">
                  <KundliChart
                    :planets="navamsaPlanets"
                    :lagnaRashi="navamsaLagnaRashi"
                  />
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="activeTab === 'positions'" class="bg-white p-6 rounded-xl shadow-md">
            <PlanetaryPositions
              :planets="viewModel.kundli?.planets"
              :lagnaRashi="viewModel.kundli?.panchang?.lagna_rashi ?? viewModel.kundli?.panchang?.lagnaRashi"
            />
          </div>

          <div v-else-if="activeTab === 'dasha'" class="bg-white p-6 rounded-xl shadow-md">
            <VimshottariDasha :dasha="viewModel.kundli?.dasha" />
          </div>

          <div v-else class="bg-white p-6 rounded-xl shadow-md">
            <BasicDetails
              :kundli="viewModel.kundli"
              :request="viewModel.request"
              :showHeader="false"
            />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: 'Inter', sans-serif;
}
.animate-fade-in {
  animation: fadeIn 0.5s ease-in;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>