<script setup>
import { computed, ref } from 'vue'
import api from '../api/client'

const emit = defineEmits(['logged-in'])

const email = ref('')
const otp = ref('')
const step = ref('email') // 'email' | 'otp'

const loading = ref(false)
const error = ref('')
const info = ref('')

const canSend = computed(() => email.value.trim().length > 3)
const canVerify = computed(() => canSend.value && otp.value.trim().length >= 4)

const requestOtp = async () => {
  error.value = ''
  info.value = ''
  loading.value = true
  try {
    await api.post('/auth/request-otp', { email: email.value })
    step.value = 'otp'
    info.value = 'OTP sent. Please check your email.'
  } catch (e) {
    const msg = e?.response?.data?.detail || 'Failed to send OTP.'
    error.value = String(msg)
  } finally {
    loading.value = false
  }
}

const verifyOtp = async () => {
  error.value = ''
  info.value = ''
  loading.value = true
  try {
    const res = await api.post('/auth/verify-otp', { email: email.value, otp: otp.value })
    const token = res?.data?.access_token
    if (!token) throw new Error('No token returned')
    localStorage.setItem('access_token', token)
    emit('logged-in', token)
  } catch (e) {
    const msg = e?.response?.data?.detail || 'OTP verification failed.'
    error.value = String(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-purple-50 py-6 sm:py-10">
    <header class="text-center mb-6 sm:mb-10">
      <h1 class="text-3xl sm:text-4xl font-bold text-indigo-900">Kundli Hub</h1>
      <p class="text-gray-600">Login with email OTP</p>
    </header>

    <main class="container mx-auto px-4">
      <div class="max-w-lg mx-auto bg-white rounded-2xl shadow-md border border-gray-100 p-6 sm:p-8">
        <h2 class="text-xl font-bold text-gray-900">Sign in</h2>
        <p class="text-sm text-gray-500 mt-1">We’ll send a one-time code to your email.</p>

        <div v-if="error" class="mt-4 p-3 rounded-xl bg-red-50 text-red-700 border border-red-100 text-sm">
          {{ error }}
        </div>
        <div v-if="info" class="mt-4 p-3 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-100 text-sm">
          {{ info }}
        </div>

        <div class="mt-5 space-y-4">
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-1.5">Email</label>
            <input
              v-model="email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition text-base"
              :disabled="loading"
            />
          </div>

          <div v-if="step === 'otp'">
            <label class="block text-sm font-bold text-gray-700 mb-1.5">OTP</label>
            <input
              v-model="otp"
              type="text"
              inputmode="numeric"
              placeholder="Enter code"
              autocomplete="one-time-code"
              class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none transition text-base"
              :disabled="loading"
            />
          </div>

          <div class="pt-2 space-y-3">
            <button
              v-if="step === 'email'"
              type="button"
              class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-3 rounded-xl shadow-lg transition disabled:opacity-50"
              :disabled="loading || !canSend"
              @click="requestOtp"
            >
              {{ loading ? 'Sending…' : 'Send OTP' }}
            </button>

            <button
              v-else
              type="button"
              class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-3 rounded-xl shadow-lg transition disabled:opacity-50"
              :disabled="loading || !canVerify"
              @click="verifyOtp"
            >
              {{ loading ? 'Verifying…' : 'Verify & Login' }}
            </button>

            <button
              v-if="step === 'otp'"
              type="button"
              class="w-full bg-white border border-gray-200 text-gray-700 font-bold py-3 rounded-xl hover:bg-gray-50 transition disabled:opacity-50"
              :disabled="loading"
              @click="requestOtp"
            >
              Resend OTP
            </button>
          </div>

          <p class="text-xs text-gray-400">
            Tip: In local dev, OTP can be echoed in backend logs when <b>DEV_OTP_ECHO=1</b>.
          </p>
        </div>
      </div>
    </main>
  </div>
</template>
