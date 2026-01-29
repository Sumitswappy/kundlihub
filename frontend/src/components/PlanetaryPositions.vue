<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
      <h4 class="font-bold text-gray-800">Planetary Positions</h4>
      <div class="text-xs text-gray-500">Whole-sign houses from Lagna</div>
    </div>

    <div v-if="planetRows.length === 0" class="p-5 text-sm text-gray-500">
      No planetary data available.
    </div>

    <div v-else class="overflow-x-auto">
      <table class="min-w-[1060px] w-full text-sm">
        <thead class="bg-gray-50">
          <tr class="text-left text-gray-600">
            <th class="px-4 py-3 font-semibold">Planet</th>
            <th class="px-4 py-3 font-semibold">Sign</th>
            <th class="px-4 py-3 font-semibold">Sign Lord</th>
            <th class="px-4 py-3 font-semibold">Nakshatra</th>
            <th class="px-4 py-3 font-semibold">Naksh Lord</th>
            <th class="px-4 py-3 font-semibold">Degree</th>
            <th class="px-4 py-3 font-semibold">House</th>
            <th class="px-4 py-3 font-semibold">Retro(R)</th>
            <th class="px-4 py-3 font-semibold">Combust</th>
            <th class="px-4 py-3 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in planetRows" :key="row.key" class="border-t border-gray-100">
            <td class="px-4 py-3 font-semibold text-gray-900">{{ row.planet }}</td>
            <td class="px-4 py-3 text-gray-800">{{ row.sign }}</td>
            <td class="px-4 py-3 text-gray-800">{{ row.signLord }}</td>
            <td class="px-4 py-3 text-gray-800">{{ row.nakshatra }}</td>
            <td class="px-4 py-3 text-gray-800">{{ row.nakshLord }}</td>
            <td class="px-4 py-3 text-gray-800">{{ row.degree }}</td>
            <td class="px-4 py-3 text-gray-800">{{ row.house }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold"
                :class="row.retro ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-600'"
              >
                {{ row.retro ? 'Retro' : 'Direct' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold"
                :class="row.combust ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'"
              >
                {{ row.combust ? 'Yes' : 'No' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold" :class="row.statusTone">
                {{ row.status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  planets: { type: Array, default: () => [] },
  lagnaRashi: { type: [String, Number], default: null },
});

const RASHI_NAMES = {
  1: 'Aries',
  2: 'Taurus',
  3: 'Gemini',
  4: 'Cancer',
  5: 'Leo',
  6: 'Virgo',
  7: 'Libra',
  8: 'Scorpio',
  9: 'Sagittarius',
  10: 'Capricorn',
  11: 'Aquarius',
  12: 'Pisces',
};

const RASHI_LORD = {
  1: 'Mars',
  2: 'Venus',
  3: 'Mercury',
  4: 'Moon',
  5: 'Sun',
  6: 'Mercury',
  7: 'Venus',
  8: 'Mars',
  9: 'Jupiter',
  10: 'Saturn',
  11: 'Saturn',
  12: 'Jupiter',
};

const safeStr = (v) => (v === null || v === undefined || v === '' ? '—' : String(v));

const toDms = (degInSign) => {
  const n = Number(degInSign);
  if (!Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  let d = Math.floor(abs);
  let mFloat = (abs - d) * 60;
  let m = Math.floor(mFloat);
  let s = Math.round((mFloat - m) * 60);
  if (s === 60) {
    s = 0;
    m += 1;
  }
  if (m === 60) {
    m = 0;
    d += 1;
  }
  return `${d}°${m}'${s}"`;
};

const GRAHA_REL = {
  Sun: { friends: ['Moon', 'Mars', 'Jupiter'], enemies: ['Venus', 'Saturn'], neutrals: ['Mercury'] },
  Moon: { friends: ['Sun', 'Mercury'], enemies: [], neutrals: ['Mars', 'Jupiter', 'Venus', 'Saturn'] },
  Mars: { friends: ['Sun', 'Moon', 'Jupiter'], enemies: ['Mercury'], neutrals: ['Venus', 'Saturn'] },
  Mercury: { friends: ['Sun', 'Venus'], enemies: ['Moon'], neutrals: ['Mars', 'Jupiter', 'Saturn'] },
  Jupiter: { friends: ['Sun', 'Moon', 'Mars'], enemies: ['Mercury', 'Venus'], neutrals: ['Saturn'] },
  Venus: { friends: ['Mercury', 'Saturn'], enemies: ['Sun', 'Moon'], neutrals: ['Mars', 'Jupiter'] },
  Saturn: { friends: ['Mercury', 'Venus'], enemies: ['Sun', 'Moon'], neutrals: ['Mars', 'Jupiter'] },
};

const OWN_SIGNS = {
  Sun: [5],
  Moon: [4],
  Mars: [1, 8],
  Mercury: [3, 6],
  Jupiter: [9, 12],
  Venus: [2, 7],
  Saturn: [10, 11],
};

// Match your reference table for Moon: Cancer -> Mooltrikona
const MOOLTRIKONA = {
  Sun: { sign: 5, from: 0, to: 20 },
  Moon: { sign: 4, from: 0, to: 30 },
  Mars: { sign: 1, from: 0, to: 12 },
  Mercury: { sign: 6, from: 16, to: 20 },
  Jupiter: { sign: 9, from: 0, to: 10 },
  Venus: { sign: 7, from: 0, to: 15 },
  Saturn: { sign: 11, from: 0, to: 20 },
};

const getDignityStatus = (planetName, rashiNum, degInSign) => {
  const p = safeStr(planetName);
  const sign = Number(rashiNum);
  const deg = Number(degInSign);
  const isClassical = Object.prototype.hasOwnProperty.call(OWN_SIGNS, p);
  if (!isClassical || !Number.isFinite(sign)) return null;

  const mt = MOOLTRIKONA[p];
  if (mt && mt.sign === sign && Number.isFinite(deg) && deg >= mt.from && deg < mt.to) {
    return { label: 'Mooltrikona', tone: 'bg-indigo-100 text-indigo-700' };
  }

  if (OWN_SIGNS[p]?.includes(sign)) {
    return { label: 'Own Sign', tone: 'bg-sky-100 text-sky-700' };
  }

  return null;
};

const _posFrom = (fromRashi, toRashi) => {
  const a = Number(fromRashi);
  const b = Number(toRashi);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  return ((b - a + 12) % 12) + 1;
};

const _naturalRel = (planetName, lordName) => {
  const p = safeStr(planetName);
  const l = safeStr(lordName);
  if (!Object.prototype.hasOwnProperty.call(GRAHA_REL, p)) return null;
  const rel = GRAHA_REL[p];
  if (rel.friends.includes(l)) return 'friend';
  if (rel.enemies.includes(l)) return 'enemy';
  if (rel.neutrals.includes(l)) return 'neutral';
  return null;
};

const _temporaryRel = (planetRashi, lordRashi) => {
  const pos = _posFrom(planetRashi, lordRashi);
  if (!pos) return null;
  return [2, 3, 4, 10, 11, 12].includes(pos) ? 'friend' : 'enemy';
};

const getStatusFromSignLord = (planetName, planetRashi, signLordName, signLordRashi) => {
  const p = safeStr(planetName);
  const lord = safeStr(signLordName);
  if (p === '—' || lord === '—') return { label: '—', tone: 'bg-gray-100 text-gray-600' };
  if (!Object.prototype.hasOwnProperty.call(GRAHA_REL, p)) return { label: '—', tone: 'bg-gray-100 text-gray-600' };

  const natural = _naturalRel(p, lord);
  const temp = _temporaryRel(planetRashi, signLordRashi);
  if (!natural || !temp) return { label: '—', tone: 'bg-gray-100 text-gray-600' };

  const friendly = natural === 'friend' || (natural === 'neutral' && temp === 'friend');
  const enemy = (natural === 'neutral' && temp === 'enemy') || (natural === 'enemy' && temp === 'enemy');

  if (friendly) return { label: 'Friendly', tone: 'bg-green-100 text-green-700' };
  if (enemy) return { label: 'Enemy', tone: 'bg-red-100 text-red-700' };
  return { label: '—', tone: 'bg-gray-100 text-gray-600' };
};

const planetRows = computed(() => {
  const lagna = Number(props.lagnaRashi);
  const hasLagna = Number.isFinite(lagna);

  const order = ['Asc', 'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu', 'Neptune', 'Uranus', 'Pluto'];
  const list = Array.isArray(props.planets) ? props.planets : [];

  const normalized = list.map((p, idx) => {
    const name = safeStr(p?.name);
    const rashiNum = Number(p?.rashi);
    const degInSignNum = Number(p?.deg ?? (Number.isFinite(Number(p?.lon)) ? (Number(p.lon) % 30) : null));

    const sign = safeStr(p?.sign || (Number.isFinite(rashiNum) ? RASHI_NAMES[rashiNum] : null));
    const signLord = safeStr(p?.sign_lord || (Number.isFinite(rashiNum) ? RASHI_LORD[rashiNum] : null));

    const lordPlanet = list.find(x => safeStr(x?.name) === signLord);
    const signLordRashi = Number(lordPlanet?.rashi);

    const house = safeStr(p?.house ?? (hasLagna && Number.isFinite(rashiNum) ? (((rashiNum - lagna) % 12 + 12) % 12) + 1 : null));
    const nak = safeStr(p?.nakshatra);
    const nakLord = safeStr(p?.nakshatra_lord);
    const retro = Boolean(p?.retro ?? p?.retrograde ?? false);
    const combust = Boolean(p?.combust ?? false);

    const degree = toDms(degInSignNum);
    const dignityMeta = getDignityStatus(name, rashiNum, degInSignNum);
    const statusMeta = dignityMeta || getStatusFromSignLord(name, rashiNum, signLord, Number.isFinite(signLordRashi) ? signLordRashi : null);

    const displayPlanet = name === 'Asc' ? 'Ascendant' : name;

    return {
      key: `${name}-${idx}`,
      planet: displayPlanet,
      sign,
      signLord,
      nakshatra: nak,
      nakshLord: nakLord,
      degree,
      house,
      retro,
      combust,
      status: statusMeta.label,
      statusTone: statusMeta.tone,
    };
  });

  normalized.sort((a, b) => {
    const aKey = a.planet === 'Ascendant' ? 'Asc' : a.planet;
    const bKey = b.planet === 'Ascendant' ? 'Asc' : b.planet;
    const ai = order.indexOf(aKey);
    const bi = order.indexOf(bKey);
    if (ai !== -1 || bi !== -1) return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    return a.planet.localeCompare(b.planet);
  });

  return normalized;
});
</script>
