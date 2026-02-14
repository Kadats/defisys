<template>
  <div class="overflow-hidden rounded-lg border border-slate-700 bg-slate-800">
    <div class="overflow-x-auto">
      <table class="min-w-full text-left text-sm text-slate-300">
        <thead class="bg-slate-900 text-xs uppercase text-slate-400">
          <tr>
            <th class="px-6 py-3">Data</th>
            <th class="px-6 py-3">Tipo</th>
            <th class="px-6 py-3 text-right">Entrada ($)</th>
            <th class="px-6 py-3 text-right">Saída ($)</th>
            <th class="px-6 py-3 text-right">Resultado</th>
            <th class="px-6 py-3 text-right">Saldo ($)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-700">
          <tr v-for="(trade, index) in trades" :key="index" class="hover:bg-slate-700/50">
            <td class="whitespace-nowrap px-6 py-4">{{ trade.date }}</td>
            <td class="whitespace-nowrap px-6 py-4">
              <span
                class="rounded px-2 py-1 text-xs font-medium"
                :class="trade.type === 'Long' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'"
              >
                {{ trade.type }}
              </span>
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right">
              {{ formatCurrency(trade.amount_in) }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right">
              {{ formatCurrency(trade.amount_out) }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right font-medium" 
                :class="trade.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'">
              {{ trade.pnl_percent.toFixed(2) }}%
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-right text-white">
              {{ formatCurrency(trade.balance_after) }}
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
defineProps({
  trades: {
    type: Array,
    default: () => [],
  },
});

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
};
</script>