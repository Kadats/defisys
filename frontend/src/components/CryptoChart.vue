<template>
  <div ref="chartContainer" class="h-96 w-full" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { createChart } from 'lightweight-charts';

const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  },
  volume: {
    type: Array,
    default: () => [],
  },
});

const chartContainer = ref(null);
const chartRef = ref(null);
const candleSeriesRef = ref(null);
const volumeSeriesRef = ref(null);
let resizeObserver = null;

const initChart = () => {
  if (!chartContainer.value) return;

  const width = chartContainer.value.clientWidth || 600;
  const height = chartContainer.value.clientHeight || 320;

  const chart = createChart(chartContainer.value, {
    width,
    height,
    layout: {
      background: { color: '#1e293b' },
      textColor: '#e2e8f0',
    },
    grid: {
      vertLines: { color: 'rgba(148, 163, 184, 0.12)' },
      horzLines: { color: 'rgba(148, 163, 184, 0.12)' },
    },
    rightPriceScale: {
      borderVisible: false,
      scaleMargins: { top: 0.1, bottom: 0.25 },
    },
    timeScale: {
      borderVisible: false,
    },
    crosshair: {
      vertLine: { color: 'rgba(226, 232, 240, 0.2)' },
      horzLine: { color: 'rgba(226, 232, 240, 0.2)' },
    },
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: '#22c55e',
    downColor: '#ef4444',
    wickUpColor: '#22c55e',
    wickDownColor: '#ef4444',
    borderVisible: false,
  });

  const volumeSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
  });

  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
    borderVisible: false,
  });

  candleSeries.setData(props.data);
  volumeSeries.setData(props.volume);

  chartRef.value = chart;
  candleSeriesRef.value = candleSeries;
  volumeSeriesRef.value = volumeSeries;

  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { width: newWidth, height: newHeight } = entry.contentRect;
      chart.applyOptions({
        width: Math.floor(newWidth),
        height: Math.floor(newHeight),
      });
      chart.timeScale().fitContent();
    }
  });

  resizeObserver.observe(chartContainer.value);
};

onMounted(() => {
  initChart();
});

onBeforeUnmount(() => {
  if (resizeObserver && chartContainer.value) {
    resizeObserver.unobserve(chartContainer.value);
    resizeObserver.disconnect();
  }

  if (chartRef.value) {
    chartRef.value.remove();
  }
});

watch(
  () => props.data,
  (newData) => {
    if (candleSeriesRef.value) {
      candleSeriesRef.value.setData(newData || []);
    }
  },
  { deep: true }
);

watch(
  () => props.volume,
  (newVolume) => {
    if (volumeSeriesRef.value) {
      volumeSeriesRef.value.setData(newVolume || []);
    }
  },
  { deep: true }
);
</script>
