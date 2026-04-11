<template>
  <div class="overflow-hidden rounded-lg border border-slate-700 bg-slate-800">
    <div class="overflow-x-auto">
      <table class="min-w-full text-left text-sm text-slate-300">
        <thead class="bg-slate-900 text-xs uppercase text-slate-400">
          <tr>
            <th class="px-6 py-3">Data</th>
            <th class="px-6 py-3">Tipo</th>
            <th class="px-6 py-3">Fluxo</th>
            <th class="px-6 py-3 text-right">Valor ($)</th>
            <th class="px-6 py-3 text-right">PnL (%)</th>
            <th class="px-6 py-3 text-right">Saldo Pós-Op ($)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-700">
          <tr v-for="(trade, index) in sortedTrades" :key="index" :class="{'bg-slate-800/50 hover:bg-slate-700/50': index % 2 === 0, 'hover:bg-slate-700/50': index % 2 === 1}">
            <td class="whitespace-nowrap px-6 py-4 text-slate-300">{{ trade.date }}</td>
            <td class="whitespace-nowrap px-6 py-4">
              <span
                class="rounded px-2 py-1 text-xs font-semibold"
                :class="typeClass(trade.type)"
              >
                {{ trade.type }}
              </span>
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-slate-200 font-medium">
              {{ trade.flow || 'Sistema' }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right">
              {{ formatCurrency(trade.amount_in > 0 ? trade.amount_in : trade.amount_out) }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right font-semibold" 
                :class="trade.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'">
              {{ trade.pnl_percent ? trade.pnl_percent.toFixed(2) + '%' : '0.00%' }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right font-bold text-white bg-slate-900/30">
              {{ formatCurrency(trade.post_trade_equity ?? 0) }}
            </td>
          </tr>
          <tr v-if="trades.length === 0">
            <td colspan="6" class="px-6 py-8 text-center text-slate-500">
              Nenhuma simulação executada ainda.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  trades: {
    type: Array,
    default: () => [],
  },
});

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
};

const typeClass = (type) => {
  const value = String(type || '').toLowerCase();
  if (value.includes('buy') || value.includes('open') || value.includes('borrow')) {
    return 'bg-emerald-900/30 text-emerald-400 border border-emerald-600/50';
  }
  if (value.includes('close') || value.includes('repay') || value.includes('harvest')) {
    return 'bg-sky-900/30 text-sky-300 border border-sky-600/50';
  }
  return 'bg-slate-700/40 text-slate-200 border border-slate-600/50';
};

// Os trades já vêm do backend ordenados em DESC (mais recentes primeiro)
// Não inverte a ordem - apenas garante que é um array
const sortedTrades = computed(() => {
  if (!props.trades || props.trades.length === 0) {
    return [];
  }
  // Trades já estão em ordem DESC do backend - manter ordem original
  return [...props.trades];
});
</script>