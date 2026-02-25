<template>
  <div class="dashboard-shell min-h-screen">
    <div class="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-10">
      <header class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-slate-400">Hedge Fund DeFi</p>
          <h1 class="mt-2 text-3xl font-semibold text-white">Mesa Institucional de Trading</h1>
          <p class="mt-2 max-w-2xl text-sm text-slate-400">
            Dados ao vivo de tesourarias segregadas e monitoramento de posições DeFi.
          </p>
        </div>
      </header>

      <!-- AVISO: Dados ao vivo -->
      <section class="panel border-l-4 border-l-amber-500 bg-amber-900/20">
        <p class="text-sm text-amber-200">
          ⚠️ <strong>Modo Simulação</strong>: Para dados ao vivo, conecte a corretora nas configurações. 
          Para backtests, acesse a aba "Simulação".
        </p>
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

      <!-- Observação: Histórico e Gráfico estão na aba "Simulação" -->
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';

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

onMounted(async () => {
  // Dashboard carrega apenas dados ao vivo (placeholder por enquanto)
  // Implementar integração com dados de corretora aqui
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
