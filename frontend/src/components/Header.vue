<template>
  <header class="z-50 shadow-lg">
    <div class="relative bg-violet-700 bg-gradient-to-br from-violet-800 to-violet-600 px-6 py-8 rounded-t-none overflow-hidden">
      <div class="absolute -top-24 -left-24 w-64 h-64 bg-violet-500 rounded-full blur-3xl opacity-20"></div>
      <div class="absolute -bottom-24 -right-24 w-64 h-64 bg-fuchsia-500 rounded-full blur-3xl opacity-20"></div>

      <div class="relative z-10 flex flex-col gap-1">
        <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight flex items-center gap-3">
          <span class="text-2xl sm:text-4xl animate-bounce-slow">🔮</span>
          <span class="shiny-text text-white">
            Kundli <span class="text-violet-200">Hub</span>
          </span>
          
        </h1>
        
      </div>

      <div class="absolute right-6 top-1/2 -translate-y-1/2 z-10">
        <button
          type="button"
          @click="$emit('open-profile')"
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
    @click.self="$emit('close-profile')"
  >
    <div class="w-full max-w-md bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-7">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-lg font-bold text-gray-900">Profile</h3>
          <p class="text-sm text-gray-500 mt-0.5">Account details</p>
        </div>
        <button
          type="button"
          @click="$emit('close-profile')"
          class="text-gray-400 hover:text-gray-700 transition px-2 py-1"
        >
          ✕
        </button>
      </div>

      <div class="mt-5 rounded-xl border border-gray-100 bg-gray-50 p-4">
        <div class="text-xs font-bold text-gray-500 uppercase tracking-wider">Email</div>
        <div class="mt-1 text-gray-900 font-semibold break-all">{{ me?.email || '—' }}</div>
      </div>

      <div class="mt-6 flex gap-3">
        <button
          type="button"
          @click="$emit('close-profile')"
          class="flex-1 bg-white border border-gray-200 text-gray-700 font-bold py-3 rounded-xl hover:bg-gray-50 transition"
        >
          Close
        </button>
        <button
          type="button"
          @click="$emit('logout')"
          class="flex-1 bg-violet-600 hover:bg-violet-700 text-white font-black py-3 rounded-xl shadow-sm transition"
        >
          Logout
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  me: { type: Object, default: null },
  profileOpen: { type: Boolean, default: false },
})

defineEmits(['open-profile', 'close-profile', 'logout'])
</script>

<style scoped>
.shiny-text {
  background: linear-gradient(
    to right,
    #ffffff 20%,
    #f1ddff 40%,
    #f1ddff 60%,
    #ffffff 80%
  );
  background-size: 200% auto;
  color: #fff;
  background-clip: text;
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
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}
</style>
