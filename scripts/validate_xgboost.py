#!/usr/bin/env python
"""
Script de Validação — Operação XGBoost

Testa:
1. Se XGBoost foi instalado corretamente
2. Se pipeline consegue criar o novo Target
3. Se modelo treina com as 6 features
4. Feature importance ranking

Uso:
    poetry run python scripts/validate_xgboost.py
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def validate_xgboost_install():
    """Verifica se XGBoost está instalado."""
    try:
        import xgboost
        logger.info("✓ XGBoost importado com sucesso")
        logger.info(f"  Versão: {xgboost.__version__}")
        return True
    except ImportError as e:
        logger.error(f"✗ XGBoost não instalado: {e}")
        return False

def validate_pipeline():
    """Verifica se pipeline cria o novo Target."""
    try:
        from backend.src.data.pipeline import get_full_prepared_data
        
        logger.info("Carregando dados do pipeline...")
        df = get_full_prepared_data()
        
        if df.empty:
            logger.warning("Pipeline retornou DataFrame vazio (possível falha de conexão com DB)")
            return False
        
        # Verificar features
        expected_features = ['RSI', 'dist_from_ema_50', 'BB_Width', 'FundingRate', 'OpenInterest', 'VolumeUSD']
        missing = [f for f in expected_features if f not in df.columns]
        
        if missing:
            logger.error(f"✗ Features faltando: {missing}")
            return False
        
        logger.info(f"✓ Pipeline criou todas as 6 features esperadas")
        
        # Verificar target
        if 'Target_Trend' not in df.columns:
            logger.error("✗ Target_Trend não foi criado")
            return False
        
        logger.info(f"✓ Target_Trend criado com sucesso")
        
        # Estatísticas
        target_dist = df['Target_Trend'].value_counts()
        logger.info(f"  Distribuição de Target:")
        logger.info(f"    Classe 0 (Sem Trend): {target_dist.get(0, 0)} amostras")
        logger.info(f"    Classe 1 (Com Trend): {target_dist.get(1, 0)} amostras")
        
        balance_ratio = target_dist.get(1, 1) / target_dist.get(0, 1)
        logger.info(f"  Razão (Trend/No-Trend): {balance_ratio:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Erro ao validar pipeline: {e}")
        return False

def validate_model_training():
    """Verifica se modelo XGBoost treina com os dados."""
    try:
        from backend.src.data.pipeline import get_full_prepared_data
        from backend.src.ai.prediction import train_prediction_model
        
        logger.info("Carregando dados para treinamento...")
        df = get_full_prepared_data()
        
        if df.empty:
            logger.warning("Dados vazios, pulando treinamento")
            return False
        
        logger.info("Treinando modelo XGBoost...")
        model, scaler = train_prediction_model(df)
        
        if model is None or scaler is None:
            logger.error("✗ Falha ao treinar modelo")
            return False
        
        logger.info("✓ Modelo XGBoost treinado com sucesso")
        
        # Verificar feature importance
        try:
            importances = model.feature_importances_
            from backend.src.ai.prediction import FEATURES
            
            ranked = sorted(zip(FEATURES, importances), key=lambda x: x[1], reverse=True)
            logger.info("Feature Importance Ranking:")
            for i, (feat, imp) in enumerate(ranked, 1):
                logger.info(f"  {i}. {feat}: {imp:.4f}")
            
            return True
        except Exception as e:
            logger.warning(f"Erro ao extrair feature importance: {e}")
            return True  # Modelo treinou, mas erro em features
        
    except Exception as e:
        logger.error(f"✗ Erro ao treinar modelo: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todas as validações."""
    logger.info("=" * 60)
    logger.info("VALIDAÇÃO — Operação XGBoost")
    logger.info("=" * 60)
    
    checks = [
        ("XGBoost Instalado", validate_xgboost_install),
        ("Pipeline (6 Features + Target)", validate_pipeline),
        ("Model Training", validate_model_training),
    ]
    
    results = []
    for name, check_fn in checks:
        logger.info(f"\n▶ Verificando: {name}")
        result = check_fn()
        results.append((name, result))
    
    # Resumo
    logger.info("\n" + "=" * 60)
    logger.info("RESUMO")
    logger.info("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\nTotal: {passed}/{total} verificações passaram")
    
    if passed == total:
        logger.info("\n🎉 Tudo validado! Operação XGBoost pronta para produção.")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} verificação(ões) falharam. Verifique os logs acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
