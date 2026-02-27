<template>
  <div class="p-6">
    <!-- Toast de Sucesso -->
    <Transition name="fade">
      <div v-if="showSuccessToast" class="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-2 animate-pulse z-50">
        <span>✅</span>
        <span>{{ successMessage }}</span>
      </div>
    </Transition>

    <!-- GOD MODE: Painel de Controle Superior -->
    <div class="mb-8 rounded-lg border border-slate-700 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 shadow-xl">
      <h2 class="mb-4 text-lg font-bold text-white">🎛️ Controle de Simulação (God Mode)</h2>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Capital Inicial ($)</label>
          <input
            v-model.number="controlParams.initialCapital"
            type="number"
            placeholder="1000"
            class="w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Dias de Simulação</label>
          <input
            v-model.number="controlParams.simulationDays"
            type="number"
            placeholder="30"
            class="w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Estratégia</label>
          <select
            v-model="selectedStrategy"
            class="w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
          >
            <option value="accumulator">Acumular BTC (Accumulator)</option>
            <option value="btc_lite">Reserva Inteligente (BTC Lite)</option>
            <option value="swing_usd">Maximizar Dólar (Swing USD)</option>
          </select>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-3 cursor-pointer px-4 py-2 rounded border border-slate-600 bg-slate-900 hover:bg-slate-800 transition">
            <input
              v-model="useLlm"
              type="checkbox"
              class="w-4 h-4 rounded border-slate-500 bg-slate-900 cursor-pointer accent-blue-500"
            />
            <span class="text-sm font-medium text-slate-300">Usar IA (Gemini)</span>
          </label>
        </div>
        <div class="flex items-end gap-2">
          <button
            @click="trainModel"
            :disabled="isTraining || isSimulating"
            class="flex-1 flex items-center justify-center rounded bg-gradient-to-r from-purple-600 to-purple-700 px-4 py-2 font-bold text-white hover:from-purple-700 hover:to-purple-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="isTraining" class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
            <span v-if="isTraining">Treinando...</span>
            <span v-else>🤖 Treinar Modelo</span>
          </button>
          <button
            @click="runSimulation"
            :disabled="isSimulating || isTraining"
            class="flex-1 flex items-center justify-center rounded bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-2 font-bold text-white hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="isSimulating" class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
            <span v-if="isSimulating">Simulando...</span>
            <span v-else>▶ Simular</span>
          </button>
        </div>
      </div>
    </div>

    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-white">📊 Simulação de Estratégia</h1>
    </div>

    <!-- Linha 1: Métricas em USD -->
    <h2 class="mb-3 text-lg font-semibold text-white">Performance em Dólar (USD)</h2>
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

    <!-- Linha 2: Métricas em Token (BTC) -->
    <h2 class="mb-3 text-lg font-semibold text-white">Performance em Token (BTC)</h2>
    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard 
        label="Alpha vs HOLD" 
        :value="tokenKpis.alpha_vs_hold.toFixed(2) + '%'" 
        :trend="tokenKpis.alpha_vs_hold" 
      />
      <StatCard 
        label="Saldo Inicial (BTC)" 
        :value="tokenKpis.initial_token_balance.toFixed(6)" 
      />
      <StatCard 
        label="Saldo Final (BTC)" 
        :value="tokenKpis.final_token_balance.toFixed(6)" 
      />
      <StatCard 
        label="ROI (Acúmulo Token)" 
        :value="tokenKpis.token_roi.toFixed(2) + '%'" 
        :trend="tokenKpis.token_roi" 
      />
    </div>

    <!-- Tesourarias Isoladas: 3 Carteiras Distintas -->
    <h2 class="mb-4 text-lg font-semibold text-white">💼 Tesourarias Isoladas</h2>
    <div class="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
      <!-- SPOT Wallet -->
      <div class="rounded-lg border border-emerald-600/30 bg-gradient-to-br from-slate-900 to-emerald-900/20 p-6">
        <h3 class="mb-4 flex items-center text-lg font-semibold text-emerald-400">
          <span class="mr-2">🏦</span> Bot Wallet (Spot)
        </h3>
        <div class="space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">USD Disponível</span>
            <span class="font-semibold text-white">{{ formatCurrency(treasuries.spot.usd_available) }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">BTC em HODL</span>
            <span class="font-semibold text-white">{{ treasuries.spot.btc_balance.toFixed(6) }} BTC</span>
          </div>
          <div class="h-px bg-slate-700/50"></div>
          <div class="flex justify-between text-sm font-bold">
            <span class="text-slate-300">Total</span>
            <span class="text-emerald-400">{{ formatCurrency(treasuries.spot.total_usd) }}</span>
          </div>
        </div>
      </div>

      <!-- DeFi LP Positions -->
      <div class="rounded-lg border border-amber-600/30 bg-gradient-to-br from-slate-900 to-amber-900/20 p-6">
        <h3 class="mb-4 flex items-center text-lg font-semibold text-amber-400">
          <span class="mr-2">🌾</span> DeFi LPs (Yield)
        </h3>
        <div class="space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">Capital Alocado</span>
            <span class="font-semibold text-white">{{ formatCurrency(treasuries.defi.capital_allocated) }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">Posições Ativas</span>
            <span class="font-semibold text-white">{{ treasuries.defi.active_positions }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">Fees Ganhos</span>
            <span class="font-semibold text-amber-400">+{{ formatCurrency(treasuries.defi.fees_earned) }}</span>
          </div>
        </div>
      </div>

      <!-- AAVE Lending -->
      <div class="rounded-lg border border-purple-600/30 bg-gradient-to-br from-slate-900 to-purple-900/20 p-6">
        <h3 class="mb-4 flex items-center text-lg font-semibold text-purple-400">
          <span class="mr-2">👻</span> AAVE (Crédito)
        </h3>
        <div class="space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">Colateral (BTC)</span>
            <span class="font-semibold text-white">{{ formatCurrency(treasuries.aave.collateral_btc_usd) }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-slate-400">Dívida (Borrow)</span>
            <span class="font-semibold text-red-400">{{ formatCurrency(treasuries.aave.debt_borrow_usd) }}</span>
          </div>
          <div class="h-px bg-slate-700/50"></div>
          <div class="flex justify-between text-sm font-bold">
            <span class="text-slate-300">Health Factor</span>
            <span :class="{
              'text-green-400': treasuries.aave.health_factor >= 1.5,
              'text-yellow-400': treasuries.aave.health_factor >= 1.2 && treasuries.aave.health_factor < 1.5,
              'text-red-400': treasuries.aave.health_factor < 1.2 && treasuries.aave.health_factor > 0
            }">
              {{ treasuries.aave.health_factor.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <h2 class="mb-4 text-lg font-semibold text-white">Histórico de Operações</h2>
    <TradesTable :trades="trades" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import StatCard from '../components/StatCard.vue';
import TradesTable from '../components/TradesTable.vue';

// Estados de carregamento independentes
const isTraining = ref(false);
const isSimulating = ref(false);
const trades = ref([]);
const showSuccessToast = ref(false);
const successMessage = ref('');

const kpis = ref({
  total_trades: 0,
  initial_balance: 0,
  final_balance: 0,
  roi: 0,
});
const tokenKpis = ref({
  alpha_vs_hold: 0,
  initial_token_balance: 0,
  final_token_balance: 0,
  token_roi: 0,
});

const controlParams = ref({
  initialCapital: 1000,
  simulationDays: 30,
});

const selectedStrategy = ref('accumulator');
const useLlm = ref(false);

const treasuries = ref({
  spot: {
    label: "🏦 Bot Wallet (Spot)",
    usd_available: 0,
    btc_balance: 0,
    btc_price: 0,
    total_usd: 0
  },
  defi: {
    label: "🌾 DeFi LPs (Yield)",
    capital_allocated: 0,
    active_positions: 0,
    fees_earned: 0,
  },
  aave: {
    label: "👻 AAVE (Crédito)",
    collateral_btc_usd: 0,
    debt_borrow_usd: 0,
    health_factor: 0,
    health_status: "NONE"
  },
  summary: {
    initial_capital: 0,
    total_equity: 0,
    roi_percent: 0,
    benchmark_roi_percent: 0
  }
});

const formatCurrency = (val) => 
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

// Helper para mostrar toast de sucesso
const showToast = (message, duration = 4000) => {
  successMessage.value = message;
  showSuccessToast.value = true;
  setTimeout(() => {
    showSuccessToast.value = false;
  }, duration);
};

const fetchData = async () => {
  try {
    const res = await fetch('/api/simulation');
    if (!res.ok) throw new Error('Falha ao buscar dados');
    const data = await res.json();
    
    // CRITICAL: Use the OFFICIAL summary from the backend
    if (data.summary) {
      // Atualizar KPIs
      kpis.value = {
        total_trades: data.summary.total_trades || 0,
        initial_balance: data.summary.initial_capital || 0,
        final_balance: data.summary.total_equity || 0,
        roi: data.summary.roi_percent || 0,
      };
      
      // Atualizar Token KPIs
      tokenKpis.value = {
        alpha_vs_hold: data.summary.alpha_vs_hold || 0,
        initial_token_balance: data.summary.initial_token_balance || 0,
        final_token_balance: data.summary.final_token_balance || 0,
        token_roi: data.summary.token_roi || 0,
      };
      
      // Atualizar Tesourarias Isoladas - Mapeado EXATAMENTE do backend
      treasuries.value = {
        spot: {
          label: "🏦 Bot Wallet (Spot)",
          usd_available: data.summary.wallet_spot_usd || 0,
          btc_balance: data.summary.wallet_spot_btc || 0,
          btc_price: 0, // Não necessário agora, pois temos total_usd
          total_usd: data.summary.wallet_spot_total_usd || 0
        },
        defi: {
          label: "🌾 DeFi LPs (Yield)",
          capital_allocated: data.summary.wallet_lp_value_usd || 0,
          active_positions: data.summary.lp_active_count || 0,
          fees_earned: data.summary.lp_fees_usd || 0,
        },
        aave: {
          label: "👻 AAVE (Crédito)",
          collateral_btc_usd: data.summary.aave_collateral_usd || 0,
          debt_borrow_usd: data.summary.aave_debt_usd || 0,
          health_factor: data.summary.aave_health_factor || 0,
        },
        summary: {
          initial_capital: data.summary.initial_capital || 0,
          total_equity: data.summary.total_equity || 0,
          roi_percent: data.summary.roi_percent || 0,
          benchmark_roi_percent: data.summary.benchmark_roi_percent || 0
        }
      };
      
      console.log('✓ Using OFFICIAL values from Backend Summary:', kpis.value);
      console.log('✓ Tesourarias:', treasuries.value);
    } else {
      // Fallback to KPIs if summary not available
      kpis.value = {
        total_trades: data.kpis.total_trades || 0,
        initial_balance: data.kpis.initial_balance || 0,
        final_balance: data.kpis.final_balance || 0,
        roi: data.kpis.roi || 0,
      };
      console.warn('⚠ Using KPIs (backend hasn\'t persisted summary yet):', kpis.value);
    }
    
    // Trades já inclui post_trade_equity e estão ordenados DESC
    trades.value = data.trades || [];
    console.log('✓ Trades com post_trade_equity em ordem DESC:', trades.value);
  } catch (error) {
    console.error('Erro ao buscar dados:', error);
  }
};

const trainModel = async () => {
  isTraining.value = true;
  try {
    console.log('🤖 Iniciando treinamento do modelo de ML...');
    const response = await fetch('/api/model/train', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Erro ao treinar modelo: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('✅ Modelo treinado com sucesso:', data);
    
    showToast(`✅ ${data.message}`, 5000);
    
  } catch (error) {
    console.error("❌ Erro ao treinar modelo:", error);
    showToast(`❌ Erro no treinamento: ${error.message}`, 5000);
  } finally {
    isTraining.value = false;
  }
};

const runSimulation = async () => {
  isSimulating.value = true;
  try {
    // 1. Dispara a simulação no backend
    console.log('🚀 Iniciando nova simulação...');
    const runRes = await fetch('/api/simulation/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        initial_capital: controlParams.value.initialCapital,
        simulation_days: controlParams.value.simulationDays,
        strategy_type: selectedStrategy.value,
        use_llm: useLlm.value,
      }),
    });
    
    if (!runRes.ok) {
      // Tratamento específico para erro 400 (modelo não treinado)
      if (runRes.status === 400) {
        const errorData = await runRes.json();
        throw new Error(errorData.detail || 'Modelo não treinado. Por favor, execute o treinamento antes de simular.');
      }
      throw new Error(`Erro ao iniciar simulação: ${runRes.statusText}`);
    }
    
    const runData = await runRes.json();
    
    // Mostrar toast de sucesso imediatamente
    if (runData.status === 'started') {
      showToast('✅ Simulação iniciada em background. Aguarde alguns segundos...');
    }
    
    // 2. Polling inteligente usando endpoint de status
    let tentativas = 0;
    const maxTentativas = 40; // até 2+ minutos
    
    const checkStatus = async () => {
      while (tentativas < maxTentativas) {
        tentativas++;
        
        // Primeira tentativa após 8s, depois a cada 3s
        const delay = tentativas === 1 ? 8000 : 3000;
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
          const statusRes = await fetch('/api/simulation/status');
          const status = await statusRes.json();
          
          console.log(`📊 Status (tentativa ${tentativas}):`, {
            running: status.running,
            trades: status.trades_count,
            hasResults: status.has_results
          });
          
          // Se não está mais rodando E tem resultados
          if (!status.running && status.has_results) {
            // CRITICAL FIX: Handle zero trades case
            if (status.trades_count === 0) {
              console.log('⚠️ Simulação concluída mas nenhuma operação foi realizada!');
              showToast('⚠️ Simulação concluída: Nenhuma operação foi realizada no período. Market conditions não atingiram os critérios de entrada.', 7000);
              try {
                await fetchData();
              } catch (e) {
                console.error('Erro ao recarregar dados:', e);
              } finally {
                isSimulating.value = false;
              }
              return;
            }
            
            console.log(`✅ Simulação concluída com ${status.trades_count} trades!`);
            showToast(`✅ Simulação concluída! ${status.trades_count} trades executados.`);
            
            // Wrap fetchData in try/catch/finally to ensure isSimulating is always reset
            try {
              await fetchData();
            } catch (e) {
              console.error('Erro ao recarregar dados após simulação:', e);
              showToast('⚠️ Erro ao carregar resultados. Tente recarregar a página.', 5000);
            } finally {
              isSimulating.value = false;
            }
            return;
          }
        } catch (e) {
          console.warn(`⚠️ Erro na tentativa ${tentativas}:`, e.message);
        }
      }
      
      console.warn('⚠️ Timeout: simulação não concluiu em 2+ minutos');
      showToast('⚠️ Simulação ainda em andamento. Recarregando dados...', 5000);
      isSimulating.value = false;
      await fetchData(); // Recarrega mesmo assim
    };
    
    // Executa polling
    checkStatus();
    
  } catch (error) {
    console.error("❌ Erro ao rodar simulação:", error);
    
    // Alerta específico para modelo não treinado
    if (error.message.includes('Modelo não treinado') || error.message.includes('treinamento antes de simular')) {
      showToast('⚠️ É necessário treinar o modelo antes de rodar a simulação! Clique em "Treinar Modelo" primeiro.', 7000);
    } else {
      showToast(`❌ Erro: ${error.message}`, 5000);
    }
    isSimulating.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>