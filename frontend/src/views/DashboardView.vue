<template>
  <div class="dashboard-shell min-h-screen">
    <div class="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-10">
      <header class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-slate-400">Hedge Fund DeFi</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">Mesa Institucional de Simulacao</h1>
          <p class="mt-2 max-w-2xl text-sm text-slate-400">
            Controle integrado de simulacoes, tesourarias segregadas e fluxo DeFi.
          </p>
        </div>
      </header>

      <section class="panel">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-white">Controles de Simulacao</h2>
            <p class="text-sm text-slate-400">Defina o periodo e o capital para o backtest.</p>
          </div>
          <button
            @click="runSimulation"
            :disabled="isRunning"
            class="inline-flex items-center gap-2 rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span v-if="isRunning" class="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent"></span>
            {{ isRunning ? 'Rodando...' : 'Rodar Simulacao' }}
          </button>
        </div>
        <div class="mt-6 grid gap-4 sm:grid-cols-3">
          <label class="control">
            <span>Data de Inicio</span>
            <input v-model="startDate" type="date" />
          </label>
          <label class="control">
            <span>Data de Fim</span>
            <input v-model="endDate" type="date" />
          </label>
          <label class="control">
            <span>Capital Inicial (USD)</span>
            <input v-model.number="initialCapital" type="number" min="0" step="50" />
          </label>
        </div>
      </section>

      <section class="grid gap-6 lg:grid-cols-3">
        <div class="panel">
          <h3 class="text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">Bot Wallet (Spot)</h3>
          <div class="mt-4 grid gap-4">
            <div class="metric-card">
              <span>Caixa Disponivel</span>
              <strong>{{ formatCurrency(summary.wallet_spot_usd) }}</strong>
            </div>
            <div class="metric-card">
              <span>Saldo BTC</span>
              <strong>{{ formatBtc(summary.wallet_spot_btc) }}</strong>
            </div>
            <div class="metric-card">
              <span>Valor Total (USD)</span>
              <strong>{{ formatCurrency(summary.wallet_spot_total_usd) }}</strong>
            </div>
          </div>
        </div>

        <div class="panel">
          <h3 class="text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">DeFi (Liquidity Pools)</h3>
          <div class="mt-4 grid gap-4">
            <div class="metric-card">
              <span>Capital Alocado</span>
              <strong>{{ formatCurrency(summary.wallet_lp_value_usd) }}</strong>
            </div>
            <div class="metric-card">
              <span>LPs Ativos</span>
              <strong>{{ summary.lp_active_count ?? 0 }}</strong>
            </div>
            <div class="metric-card">
              <span>Taxas Farmadas</span>
              <strong>{{ formatCurrency(summary.lp_fees_usd) }}</strong>
            </div>
          </div>
        </div>

        <div class="panel">
          <h3 class="text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">AAVE (Credit Line)</h3>
          <div class="mt-4 grid gap-4">
            <div class="metric-card">
              <span>Colateral Fornecido</span>
              <strong>{{ formatCurrency(summary.aave_collateral_usd) }}</strong>
            </div>
            <div class="metric-card">
              <span>Divida (Borrow)</span>
              <strong>{{ formatCurrency(summary.aave_debt_usd) }}</strong>
            </div>
            <div class="metric-card">
              <span>Health Factor</span>
              <strong :class="healthFactorClass(summary.aave_health_factor)">
                {{ formatNumber(summary.aave_health_factor) }}
              </strong>
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2 class="text-lg font-semibold text-white">Historico de Operacoes</h2>
        <div class="mt-4">
          <TradesTable :trades="trades" />
        </div>
      </section>

      <section class="panel">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-white">Grafico de Preco</h2>
          <span class="text-xs text-slate-400">BTCUSDT 4H</span>
        </div>
        <div v-if="isLoading" class="mt-4 text-slate-400">Carregando...</div>
        <CryptoChart v-else :data="candles" :volume="volumes" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import CryptoChart from '../components/CryptoChart.vue';
import TradesTable from '../components/TradesTable.vue';

const candles = ref([]);
const volumes = ref([]);
const trades = ref([]);
const summary = ref({
  wallet_spot_usd: 0,
  wallet_spot_btc: 0,
  wallet_spot_total_usd: 0,
  wallet_lp_value_usd: 0,
  lp_active_count: 0,
  lp_fees_usd: 0,
  aave_collateral_usd: 0,
  aave_debt_usd: 0,
  aave_health_factor: 0,
});

const startDate = ref('');
const endDate = ref('');
const initialCapital = ref(1050);
const isLoading = ref(true);
const isRunning = ref(false);

const formatCurrency = (value) => {
  const numeric = Number(value ?? 0);
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numeric);
};

const formatBtc = (value) => {
  const numeric = Number(value ?? 0);
  return `${numeric.toFixed(6)} BTC`;
};

const formatNumber = (value) => {
  const numeric = Number(value ?? 0);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : '0.00';
};

const healthFactorClass = (value) => {
  const numeric = Number(value ?? 0);
  if (numeric >= 1.5) return 'text-emerald-400';
  if (numeric >= 1.1) return 'text-amber-400';
  return 'text-red-400';
};

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

const fetchMarketData = async () => {
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
};

const fetchSimulation = async () => {
  try {
    const response = await fetch('/api/simulation');
    if (!response.ok) throw new Error('Falha ao buscar dados');
    const data = await response.json();
    summary.value = data.summary || summary.value;
    trades.value = data.trades || [];
  } catch (error) {
    trades.value = [];
  }
};

const runSimulation = async () => {
  isRunning.value = true;
  try {
    await fetch('/api/simulation/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_date: startDate.value || null,
        end_date: endDate.value || null,
        initial_capital: initialCapital.value || null,
      }),
    });

    setTimeout(async () => {
      await fetchSimulation();
      isRunning.value = false;
    }, 5000);
  } catch (error) {
    isRunning.value = false;
  }
};

onMounted(async () => {
  await Promise.all([fetchMarketData(), fetchSimulation()]);
});
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

.dashboard-shell {
  font-family: 'Space Grotesk', 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
  background: radial-gradient(circle at top, #0b1220, #05070d 65%);
  color: #e2e8f0;
}

.panel {
  background: linear-gradient(140deg, rgba(15, 23, 42, 0.9), rgba(2, 6, 23, 0.95));
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 18px 45px rgba(2, 6, 23, 0.55);
}

.control {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.875rem;
  color: #94a3b8;
}

.control input {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  padding: 10px 12px;
  color: #f8fafc;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.08);
  color: #e2e8f0;
}

.metric-card span {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: #94a3b8;
}

.metric-card strong {
  font-size: 1.25rem;
  font-weight: 600;
}
</style>
