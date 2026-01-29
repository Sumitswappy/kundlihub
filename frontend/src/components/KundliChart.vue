<template>
  <div class="flex justify-center p-4 bg-orange-50 rounded-xl shadow-inner">
    <svg width="400" height="400" viewBox="0 0 300 300" class="drop-shadow-lg">
      <rect width="300" height="300" fill="white" stroke="#c05621" stroke-width="4" />

      <line x1="0" y1="0" x2="300" y2="300" stroke="#c05621" stroke-width="2" />
      <line x1="300" y1="0" x2="0" y2="300" stroke="#c05621" stroke-width="2" />
      <line x1="150" y1="0" x2="300" y2="150" stroke="#c05621" stroke-width="2" />
      <line x1="300" y1="150" x2="150" y2="300" stroke="#c05621" stroke-width="2" />
      <line x1="150" y1="300" x2="0" y2="150" stroke="#c05621" stroke-width="2" />
      <line x1="0" y1="150" x2="150" y2="0" stroke="#c05621" stroke-width="2" />

      <g v-for="(house, index) in housePositions" :key="index">
        <text
          :x="house.rX"
          :y="house.rY"
          font-size="13"
          fill="#7b341e"
          font-weight="bold"
          text-anchor="middle"
        >
          {{ getRashiForHouse(index + 1) }}
        </text>

        <text
          :x="house.pX"
          :y="house.pY"
          font-size="11"
          fill="#2d3748"
          text-anchor="middle"
          font-family="sans-serif"
        >
          <tspan
            v-for="(p, pIdx) in getPlanetsInHouse(index + 1)"
            :key="p"
            :x="house.pX"
            :dy="pIdx === 0 ? calculateVerticalCentering(index + 1) : '1.2em'"
          >
            {{ p }}
          </tspan>
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup>
const props = defineProps({
  planets: { type: Array, default: () => [] },
  lagnaRashi: { type: [String, Number], default: null },
});

// Coordinates tuned for your North Indian chart layout
const housePositions = [
  { rX: 150, rY: 135, pX: 150, pY: 70 }, // 1
  { rX: 75, rY: 65, pX: 75, pY: 35 }, // 2
  { rX: 55, rY: 80, pX: 30, pY: 70 }, // 3
  { rX: 130, rY: 155, pX: 75, pY: 155 }, // 4
  { rX: 55, rY: 230, pX: 30, pY: 230 }, // 5
  { rX: 75, rY: 245, pX: 75, pY: 275 }, // 6
  { rX: 150, rY: 175, pX: 150, pY: 230 }, // 7
  { rX: 225, rY: 245, pX: 230, pY: 275 }, // 8
  { rX: 240, rY: 230, pX: 275, pY: 230 }, // 9
  { rX: 170, rY: 155, pX: 230, pY: 155 }, // 10
  { rX: 240, rY: 80, pX: 275, pY: 70 }, // 11
  { rX: 225, rY: 65, pX: 230, pY: 35 }, // 12
];

const getRashiForHouse = (houseNum) => {
  const lagna = Number(props.lagnaRashi);
  if (!Number.isFinite(lagna)) return '—';
  return ((lagna - 1 + (houseNum - 1)) % 12) + 1;
};

const getPlanetsInHouse = (houseNum) => {
  const rashi = getRashiForHouse(houseNum);
  if (rashi === '—' || !Array.isArray(props.planets)) return [];

  const abbr = {
    Asc: 'Asc',
    Sun: 'Su',
    Moon: 'Mo',
    Mars: 'Ma',
    Mercury: 'Me',
    Jupiter: 'Ju',
    Venus: 'Ve',
    Saturn: 'Sa',
    Rahu: 'Ra',
    Ketu: 'Ke',
    Uranus: 'Ur',
    Neptune: 'Ne',
    Pluto: 'Pl',
  };

  return props.planets
    .filter((p) => Number(p?.rashi) === Number(rashi))
    .map((p) => {
      const code = abbr[p?.name] || String(p?.name || '').substring(0, 2);
      const deg = Number.isFinite(Number(p?.deg)) ? Number(p.deg) : (Number(p?.lon || 0) % 30);
      return `${code}-${deg.toFixed(1)}°`;
    });
};

const calculateVerticalCentering = (houseNum) => {
  const count = getPlanetsInHouse(houseNum).length;
  if (count <= 1) return '0';
  return `-${(count - 1) * 0.4}em`;
};
</script>