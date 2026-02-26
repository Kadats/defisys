import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERRO: GEMINI_API_KEY não encontrada no ambiente.")
    exit(1)

# Configura a API exatamente como manda o seu AI_INSTRUCTIONS.md
genai.configure(api_key=api_key, transport="rest")
model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

print(f"🚀 Iniciando teste isolado com o modelo: {model_name}")

# Instancia o modelo forçando a saída em JSON
model = genai.GenerativeModel(
    model_name=model_name,
    generation_config=genai.GenerationConfig(
        temperature=0.1,
        response_mime_type="application/json", # Isso força a API a retornar apenas JSON
    )
)

# Um prompt simulando o contexto do seu TradingEngine
prompt = """
You are a crypto trading bot. Analyze this context and return a JSON decision.
Context: BTC is at $88,000. RSI is 35. Trend is sideways.
Expected JSON format strictly like this:
{
  "decision": "SPOT_ONLY",
  "allocation_pct": 10,
  "reason": "Testing the API response format"
}
"""

print("⏳ Enviando requisição para o Google Gemini...\n")

try:
    response = model.generate_content(prompt)
    raw_text = response.text
    
    print("==========================================")
    print("  RESPOSTA BRUTA (RAW) RETORNADA PELA API ")
    print("==========================================")
    # Usamos repr() para ver se existem quebras de linha (\n) ou blocos markdown escondidos
    print(repr(raw_text)) 
    print("==========================================\n")

    print("🔍 Tentando fazer o parse (json.loads)...")
    parsed_json = json.loads(raw_text)
    
    print("✅ SUCESSO! O Python conseguiu ler como JSON válido:")
    print(json.dumps(parsed_json, indent=2))

except Exception as e:
    print(f"❌ FALHA AO PROCESSAR: {type(e).__name__} - {e}")