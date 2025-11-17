import logging
import sys
import os
from .config import PROJECT_ROOT

def setup_logging(level=None):
    """
    Configura o logger raiz para escrever no console (stdout) e em um arquivo.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    elif not isinstance(level, int):
        level = logging.INFO

    # 1. Definir o formato dos logs
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 2. Obter o logger raiz
    root = logging.getLogger()
    root.setLevel(level)
    
    # Limpar handlers antigos para evitar duplicação se a função for chamada 2x
    if root.handlers:
        root.handlers.clear()

    # 3. Handler do Console (StreamHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # 4. Handler de Arquivo (FileHandler)
    # Cria a pasta 'logs' se não existir
    log_dir = os.path.join(PROJECT_ROOT, 'backend', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'defisys.log')
    
    # 'a' = append (adiciona ao final), 'w' = write (sobrescreve a cada execução)
    # Vamos usar 'w' para ter um log limpo a cada execução do sistema, 
    # mas se quiser histórico eterno, mude para 'a'.
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Logger específico do projeto
    logger = logging.getLogger("defisys")
    logger.setLevel(level)
    
    # Teste inicial
    logger.info(f"Sistema de logs iniciado. Gravando em: {log_file}")
    
    return logger
