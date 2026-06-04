from deep_translator import GoogleTranslator


def traduzir_texto(texto, idioma_destino='pt'):
    """Traduz um texto para o idioma de destino usando o Google Translator.
    
    Args:
        texto: Texto a ser traduzido.
        idioma_destino: Código do idioma de destino (padrão: 'pt' para português).
        
    Returns:
        Texto traduzido, ou o texto original em caso de falha.
    """
    if not texto or not texto.strip():
        return texto
    try:
        return GoogleTranslator(source='auto', target=idioma_destino).translate(texto)
    except Exception as e:
        print(f"  [Aviso] Falha na tradução: {e}")
        return texto
