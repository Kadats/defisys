<template>
  <div class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-white">Simulação de Estratégia</h1>
      <button
        @click="runSimulation"
        :disabled="isRunning"
        class="flex items-center rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        <span v-if="isRunning" class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
        {{ isRunning ? 'Simulando...' : 'Rodar Nova Simulação' }}
      </button>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Total de Trades" :value="kpis.total_trades" />
      <StatCard label="Saldo Inicial" :value="formatCurrency(kpis.initial_balance)" />
      <StatCard label="Saldo Final" :value="formatCurrency(kpis.final_balance)" />
      <StatCard 
        label="ROI (Retorno)" 
        :value="kpis.roi.toFixed(2) + '%'" 
        :trend="kpis.roi" 
      />
    </div>

    <h2 class="mb-4 text-lg font-semibold text-white">Histórico de Operações</h2>
    <TradesTable :trades="trades" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import StatCard from '../components/StatCard.vue';
import TradesTable from '../components/TradesTable.vue';

const isRunning = ref(false);
const trades = ref([]);
const kpis = ref({
  total_trades: 0,
  initial_balance: 0,
  final_balance: 0,
  roi: 0,
});

const formatCurrency = (val) => 
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

const fetchData = async () => {
  try {
    const res = await fetch('/api/simulation');
    if (!res.ok) throw new Error('Falha ao buscar dados');
    const data = await res.json();
    
    // CRITICAL FIX: Use the OFFICIAL summary from the backend, not calculated values
    // The Backend is the "Source of Truth"
    if (data.summary) {
      // Use the official summary that was persisted by the backend
      kpis.value = {
        total_trades: data.summary.total_trades || 0,
        initial_balance: data.summary.initial_capital || 0,
        final_balance: data.summary.total_equity || 0,
        roi: data.summary.roi_percent || 0,
      };
      console.log('✓ Using OFFICIAL values from Backend Summary:', kpis.value);
    } else {
      // Fallback to KPIs if summary not available (shouldn't happen after first run)
      kpis.value = {
        total_trades: data.kpis.total_trades || 0,
        initial_balance: data.kpis.initial_balance || 0,
        final_balance: data.kpis.final_balance || 0,
        roi: data.kpis.roi || 0,
      };
      console.warn('⚠ Using KPIs (backend hasn\'t persisted summary yet):', kpis.value);
    }
    
    trades.value = data.trades || [];
  } catch (error) {
    console.error(error);
  }
};

const runSimulation = async () => {
  isRunning.value = true;
  try {
    // 1. Dispara a simulação no backend
    await fetch('/api/simulation/run', { method: 'POST' });
    
    // 2. Aguarda um pouco para o backend começar a processar (polling simples)
    // Em um app real, usaríamos WebSocket para saber quando acabou. 
    // Por enquanto, vamos esperar 5 segundos e recarregar.
    setTimeout(async () => {
      await fetchData();
      isRunning.value = false;
    }, 5000); 
    
  } catch (error) {
    console.error("Erro ao rodar simulação:", error);
    isRunning.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>