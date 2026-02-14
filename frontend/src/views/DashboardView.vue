<template>
  <div class="p-6">
    <div class="rounded-lg bg-slate-800 p-6 text-white shadow">
      <h1 class="text-xl font-semibold">Grafico de Preco</h1>
      <div v-if="isLoading" class="mt-4 text-slate-300">Carregando...</div>
      <CryptoChart v-else :data="candles" :volume="volumes" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import CryptoChart from '../components/CryptoChart.vue';

const candles = ref([]);
const volumes = ref([]);
const isLoading = ref(true);

const normalizeTime = (value) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value > 1e12 ? Math.floor(value / 1000) : Math.floor(value);
  }

  if (typeof value === 'string') {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      return numeric > 1e12 ? Math.floor(numeric / 1000) : Math.floor(numeric);
    }

    const parsed = Date.parse(value);
    if (!Number.isNaN(parsed)) {
      return Math.floor(parsed / 1000);
    }
  }

  return undefined;
};

const buildSeries = (rows) => {
  const candleSeries = [];
  const volumeSeries = [];

  rows.forEach((row) => {
    const time = normalizeTime(row.time ?? row.timestamp ?? row.date);
    if (!time) return;

    const open = Number(row.open);
    const high = Number(row.high);
    const low = Number(row.low);
    const close = Number(row.close);
    if ([open, high, low, close].some((value) => Number.isNaN(value))) return;

    candleSeries.push({ time, open, high, low, close });

    const volume = Number(row.volume ?? row.value ?? 0);
    const isUp = close >= open;
    volumeSeries.push({
      time,
      value: Number.isNaN(volume) ? 0 : volume,
      color: isUp ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)',
    });
  });

  return { candleSeries, volumeSeries };
};

onMounted(async () => {
  try {
    const response = await fetch('/api/history');
    const payload = await response.json();
    const rows = Array.isArray(payload) ? payload : payload?.candles || [];

    const { candleSeries, volumeSeries } = buildSeries(rows);
    candles.value = candleSeries;
    volumes.value = volumeSeries;
  } catch (error) {
    candles.value = [];
    volumes.value = [];
  } finally {
    isLoading.value = false;
  }
});
</script>
