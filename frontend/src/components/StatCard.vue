<template>
  <div class="rounded-lg bg-slate-800 p-4 shadow border border-slate-700">
    <div class="text-sm text-slate-400">{{ label }}</div>
    <div class="mt-1 text-2xl font-bold" :class="colorClass">
      {{ value }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: String,
  value: [String, Number],
  trend: Number, // Opcional: se > 0 verde, < 0 vermelho
});

const colorClass = computed(() => {
  if (props.trend > 0) return 'text-green-400';
  if (props.trend < 0) return 'text-red-400';
  return 'text-white';
});
</script>