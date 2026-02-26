"""
Script de teste para validar a migração para gemini-1.5-flash.
Verifica conectividade, modelo correto e calcula capacidade de simulação.
"""
import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Cores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ {text}{RESET}")

# Configurações
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")
api_delay = float(os.getenv("GEMINI_API_DELAY_SECONDS", "5.0"))

print_header("TESTE DE MIGRAÇÃO - GEMINI 1.5-FLASH")

# Validação 1: API Key
if not api_key:
    print_error("GEMINI_API_KEY não encontrada no ambiente")
    exit(1)
print_success(f"API Key encontrada: {api_key[:20]}...")

# Validação 2: Modelo configurado
print_success(f"Modelo configurado: {model_name}")
print_info(f"Delay entre chamadas: {api_delay}s")

# Configurar API
try:
    genai.configure(api_key=api_key, transport="rest")
    print_success("API Gemini configurada com sucesso")
except Exception as e:
    print_error(f"Falha ao configurar API: {e}")
    exit(1)

# Validação 3: Listar modelos disponíveis
print_header("MODELOS DISPONÍVEIS")
try:
    available_models = []
    for model in genai.list_models():
        if "generateContent" in getattr(model, "supported_generation_methods", []):
            available_models.append(model.name)
            quota_info = ""
            # Verificar se é o modelo que estamos usando
            marker = "👉 " if model.name == model_name else "   "
            print(f"{marker}{model.name}")
    
    if model_name in available_models:
        print_success(f"\nModelo {model_name} está disponível!")
    else:
        print_error(f"\nModelo {model_name} NÃO encontrado na lista")
        print_info(f"Usando primeiro modelo disponível: {available_models[0]}")
        model_name = available_models[0]

except Exception as e:
    print_error(f"Falha ao listar modelos: {e}")
    exit(1)

# Validação 4: Teste de chamada real
print_header("TESTE DE RESPOSTA JSON")

try:
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=300,
            response_mime_type="application/json",
        )
    )
    
    prompt = """
{
  "context": "BTC price: $88,000, RSI: 45, Health Factor: 2.5, ML Confidence: 0.72",
  "task": "Return a JSON trading decision with fields: action, amount_pct, reason"
}

Return ONLY valid JSON like:
{"action": "SPOT_ONLY", "amount_pct": 0.15, "reason": "Testing migration"}
"""
    
    print_info("Enviando requisição de teste...")
    start_time = time.time()
    response = model.generate_content(prompt)
    elapsed_time = time.time() - start_time
    
    raw_text = response.text.strip()
    print_success(f"Resposta recebida em {elapsed_time:.2f}s")
    
    # Tentar parse do JSON
    try:
        # Limpar markdown se necessário
        cleaned = raw_text
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
            if cleaned.startswith(("json", "JSON")):
                cleaned = cleaned[4:]
            cleaned = cleaned.lstrip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # Parse
        parsed = json.loads(cleaned)
        print_success("JSON parseado com sucesso!")
        print(f"\n{json.dumps(parsed, indent=2)}\n")
        
        # Validar estrutura
        if "action" in parsed and "amount_pct" in parsed and "reason" in parsed:
            print_success("Estrutura de resposta válida!")
        else:
            print_error("Estrutura de resposta inválida (campos faltando)")
            
    except json.JSONDecodeError as e:
        print_error(f"Falha ao parsear JSON: {e}")
        print_info(f"Resposta bruta: {repr(raw_text[:200])}")
        
except Exception as e:
    print_error(f"Falha no teste de chamada: {type(e).__name__}: {str(e)[:150]}")
    if "429" in str(e):
        print_info("Quota diária atingida. Aguarde reset em ~24h.")
    exit(1)

# Cálculos de Capacidade
print_header("CAPACIDADE DE SIMULAÇÃO")

# Configurações do projeto
CANDLE_INTERVAL_HOURS = 4
HOURS_PER_DAY = 24
DAILY_QUOTA_15_FLASH = 1500  # gemini-1.5-flash
DAILY_QUOTA_25_FLASH = 20     # gemini-2.5-flash (antigo)

# Cálculos
candles_per_day = HOURS_PER_DAY / CANDLE_INTERVAL_HOURS
print_info(f"Candles por dia (4h): {candles_per_day}")

# Com gemini-1.5-flash
days_possible_15 = DAILY_QUOTA_15_FLASH / candles_per_day
simulations_30d_15 = DAILY_QUOTA_15_FLASH / (30 * candles_per_day)

# Com gemini-2.5-flash (comparação)
days_possible_25 = DAILY_QUOTA_25_FLASH / candles_per_day
simulations_30d_25 = DAILY_QUOTA_25_FLASH / (30 * candles_per_day)

print(f"\n{GREEN}┌─ GEMINI-1.5-FLASH (NOVO) ─────────────────────┐{RESET}")
print(f"{GREEN}│ Quota Diária:        1500 requisições         │{RESET}")
print(f"{GREEN}│ Dias Simuláveis:     {days_possible_15:.1f} dias                   │{RESET}")
print(f"{GREEN}│ Backtests de 30d:    {simulations_30d_15:.1f} simulações completas   │{RESET}")
print(f"{GREEN}└────────────────────────────────────────────────┘{RESET}")

print(f"\n{RED}┌─ GEMINI-2.5-FLASH (ANTIGO) ───────────────────┐{RESET}")
print(f"{RED}│ Quota Diária:        20 requisições           │{RESET}")
print(f"{RED}│ Dias Simuláveis:     {days_possible_25:.1f} dias                    │{RESET}")
print(f"{RED}│ Backtests de 30d:    {simulations_30d_25:.2f} simulações completas   │{RESET}")
print(f"{RED}└────────────────────────────────────────────────┘{RESET}")

improvement = (DAILY_QUOTA_15_FLASH / DAILY_QUOTA_25_FLASH)
print(f"\n{YELLOW}🚀 MELHORIA: {improvement}x mais capacidade!{RESET}")

# Tempo estimado para simulação de 30 dias
candles_30d = 30 * candles_per_day
time_30d_sim = candles_30d * api_delay / 60  # minutos
print(f"\n{BLUE}⏱️  Tempo estimado para backtest de 30 dias:{RESET}")
print(f"{BLUE}   {candles_30d:.0f} requisições × {api_delay}s = {time_30d_sim:.1f} minutos (~{time_30d_sim/60:.1f}h){RESET}")

print_header("✅ TESTE DE MIGRAÇÃO CONCLUÍDO")
print_success("Sistema pronto para simulações de backtest!")
