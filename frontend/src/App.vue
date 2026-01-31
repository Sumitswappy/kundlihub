<script setup>
import { ref, computed, watch } from 'vue'
import OtpLogin from './components/OtpLogin.vue'
import api from './api/client'
import InputForm from './components/InputForm.vue'
import KundliChart from './components/KundliChart.vue'
import PlanetaryPositions from './components/PlanetaryPositions.vue'
import VimshottariDasha from './components/VimshottariDasha.vue'
import BasicDetails from './components/BasicDetails.vue'
import Dosha from './components/Dosha.vue'
import DailyHoroscope from './components/DailyHoroscope.vue'
import SadeSati from './components/SadeSati.vue'

const token = ref(localStorage.getItem('access_token') || '')
const isLoggedIn = computed(() => Boolean(token.value))

const me = ref(null)
const profileOpen = ref(false)

const openProfile = () => {
  profileOpen.value = true
}

const closeProfile = () => {
  profileOpen.value = false
}

const fetchMe = async () => {
  if (!isLoggedIn.value) {
    me.value = null
    return
  }
  try {
    const res = await api.get('/auth/me')
    me.value = res?.data || null
  } catch (e) {
    logout()
  }
}

const onLoggedIn = (t) => {
  token.value = t
  fetchMe()
}

const logout = () => {
  localStorage.removeItem('access_token')
  token.value = ''
  me.value = null
  profileOpen.value = false
}

watch(
  () => token.value,
  () => {
    fetchMe()
  },
  { immediate: true }
)

const viewModel = ref(null)
const activeTab = ref('details')

const personName = computed(() => {
  const req = viewModel.value?.request
  return req?.full_name || req?.fullName || req?.name || ''
})

const handleKundliGenerated = (data) => {
  viewModel.value = data
  activeTab.value = 'details'
}

const reset = () => {
  viewModel.value = null
  activeTab.value = 'details'
}

const lagnaRashiValue = computed(() => {
  const k = viewModel.value?.kundli
  return k?.panchang?.lagna_rashi ?? k?.panchang?.lagnaRashi ?? null
})

const _mod12 = (n) => ((n % 12) + 12) % 12

const _navamsaStartSign = (rashiNum) => {
  const r = Number(rashiNum)
  if (!Number.isFinite(r)) return null
  if ([1, 4, 7, 10].includes(r)) return r
  if ([2, 5, 8, 11].includes(r)) return _mod12(r - 1 + 8) + 1
  return _mod12(r - 1 + 4) + 1
}

const _toNavamsa = (rashiNum, degInSign) => {
  const r = Number(rashiNum)
  const deg = Number(degInSign)
  if (!Number.isFinite(r) || !Number.isFinite(deg)) return null
  const partSize = 30 / 9
  const part = Math.min(8, Math.max(0, Math.floor(deg / partSize)))
  const start = _navamsaStartSign(r)
  if (!start) return null
  const navRashi = _mod12(start - 1 + part) + 1
  const withinPart = deg - part * partSize
  const navDeg = withinPart * 9
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
  <OtpLogin v-if="!isLoggedIn" @logged-in="onLoggedIn" />

  <div v-else class="min-h-screen bg-purple-50">
    
    <header class="sticky top-0 z-50 shadow-lg">
      <div class="relative bg-violet-700 bg-gradient-to-br from-violet-800 to-violet-600 px-6 py-8 rounded-t-none overflow-hidden">
        
        <div class="absolute -top-24 -left-24 w-64 h-64 bg-violet-500 rounded-full blur-3xl opacity-20"></div>
        <div class="absolute -bottom-24 -right-24 w-64 h-64 bg-fuchsia-500 rounded-full blur-3xl opacity-20"></div>

        <div class="relative z-10 flex flex-col gap-1">
          <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight flex items-center gap-3">
            <span class="shiny-text text-white">
              Kundli <span class="text-violet-200">Hub</span>
            </span>
            <span class="text-2xl sm:text-4xl animate-bounce-slow">🔮</span>
          </h1>
          <p class="text-violet-100/80 font-medium flex items-center gap-2">
            <span class="w-8 h-px bg-violet-400"></span>
            Premium Kundli Maker
          </p>
        </div>

        <div class="absolute right-6 top-1/2 -translate-y-1/2 z-10">
          <button
            type="button"
            @click="openProfile"
            class="group relative bg-violet-600/40 backdrop-blur-md border border-white-400/30 text-white w-12 h-12 rounded-full font-semibold hover:bg-white hover:text-violet-700 transition-all duration-300 shadow-lg inline-flex items-center justify-center overflow-hidden"
            aria-label="Profile"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-6 w-6"
            >
              <path d="M20 21a8 8 0 0 0-16 0" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </button>
        </div>
      </div>
    </header>

    <div
      v-if="profileOpen"
      class="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center px-4"
      @click.self="closeProfile"
    >
      <div class="w-full max-w-md bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-7">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900">Profile</h3>
            <p class="text-sm text-gray-500 mt-0.5">Account details</p>
          </div>
          <button type="button" @click="closeProfile" class="text-gray-400 hover:text-gray-700 transition px-2 py-1">✕</button>
        </div>
        <div class="mt-5 rounded-xl border border-gray-100 bg-gray-50 p-4">
          <div class="text-xs font-bold text-gray-500 uppercase tracking-wider">Email</div>
          <div class="mt-1 text-gray-900 font-semibold break-all">{{ me?.email || '—' }}</div>
        </div>
        <div class="mt-6 flex gap-3">
          <button @click="closeProfile" class="flex-1 bg-white border border-gray-200 text-gray-700 font-bold py-3 rounded-xl hover:bg-gray-50 transition">Close</button>
          <button @click="logout" class="flex-1 bg-violet-600 hover:bg-violet-700 text-white font-black py-3 rounded-xl shadow-sm transition">Logout</button>
        </div>
      </div>
    </div>

    <main class="container mx-auto px-4 pt-10 pb-20">
      <section v-if="!viewModel" class="w-full">
        <InputForm @submit-success="handleKundliGenerated" />
      </section>

      <section v-else class="space-y-10 animate-fade-in">
        <div class="max-w-6xl mx-auto space-y-6">
          <div class="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
            <h2 class="text-2xl font-bold text-violet-900">Kundli Details</h2>
            <button
              type="button"
              @click="reset"
              class="bg-violet-50 text-violet-700 px-4 py-2 rounded-lg font-semibold hover:bg-violet-100 transition"
            >
              ← Generate Another
            </button>
          </div>

          <div class="sticky top-[120px] z-30 sm:static">
            <div class="bg-white/95 backdrop-blur rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div class="flex flex-wrap">
                <button v-for="tab in ['details', 'chart', 'dasha', 'horoscope', 'sadesati', 'dosha']"
                  :key="tab"
                  @click="activeTab = tab"
                  class="flex-1 min-w-[140px] px-4 py-3 text-sm font-semibold transition capitalize"
                  :class="activeTab === tab ? 'bg-violet-50 text-violet-800' : 'bg-white text-gray-600 hover:bg-gray-50'"
                >
                  {{ tab.replace('sadesati', 'Sade Sati') }}
                </button>
              </div>
            </div>
          </div>

          <div class="bg-white p-4 sm:p-6 rounded-xl shadow-md">
            <template v-if="activeTab === 'details'">
              <BasicDetails :kundli="viewModel.kundli" :request="viewModel.request" :showHeader="false" />
            </template>
            <template v-else-if="activeTab === 'chart'">
              <div class="space-y-8">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
                  <div class="text-center">
                    <h3 class="text-xl font-bold mb-4">Lagna Chart</h3>
                    <div class="flex justify-center">
                      <KundliChart :planets="viewModel.kundli?.planets" :lagnaRashi="lagnaRashiValue" :personName="personName" />
                    </div>
                  </div>
                  <div class="text-center">
                    <h3 class="text-xl font-bold mb-4">Navamsa Chart</h3>
                    <div class="flex justify-center">
                      <KundliChart :planets="navamsaPlanets" :lagnaRashi="navamsaLagnaRashi" :personName="personName" />
                    </div>
                  </div>
                </div>
                <PlanetaryPositions :planets="viewModel.kundli?.planets" :lagnaRashi="viewModel.kundli?.panchang?.lagna_rashi ?? viewModel.kundli?.panchang?.lagnaRashi" />
              </div>
            </template>
            <template v-else-if="activeTab === 'dasha'">
              <VimshottariDasha :dasha="viewModel.kundli?.dasha" :personName="personName" />
            </template>
            <template v-else-if="activeTab === 'horoscope'">
              <DailyHoroscope :request="viewModel.request" :personName="personName" />
            </template>
            <template v-else-if="activeTab === 'sadesati'">
              <SadeSati :request="viewModel.request" :personName="personName" />
            </template>
            <template v-else-if="activeTab === 'dosha'">
              <Dosha :doshas="viewModel.kundli?.doshas" :personName="personName" />
            </template>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
body { margin: 0; font-family: 'Inter', sans-serif; }
.animate-fade-in { animation: fadeIn 0.5s ease-in; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #7c3aed; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #a78bfa; }
.shiny-text {
  background: linear-gradient(
    to right,
    #ffffff 20%,
    #ddd6fe 40%,
    #ddd6fe 60%,
    #ffffff 80%
  );
  background-size: 200% auto;
  color: #fff;
  background-clip: text;
  text-fill-color: transparent;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shine 4s linear infinite;
}

@keyframes shine {
  to {
    background-position: 200% center;
  }
}

.animate-bounce-slow {
  animation: bounce-slow 3s ease-in-out infinite;
}

@keyframes bounce-slow {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}
</style>