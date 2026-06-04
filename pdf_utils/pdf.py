import re
import PyPDF2
import fitz  # PyMuPDF


def extrair_texto_pdf(caminho_pdf, max_paginas=2):
    """Extrai o texto das primeiras páginas de um arquivo PDF.
    
    Args:
        caminho_pdf: Caminho absoluto para o arquivo PDF.
        max_paginas: Número máximo de páginas a serem lidas (padrão: 2).
        
    Returns:
        String com o texto extraído, ou string vazia em caso de falha.
    """
    texto_extraido = ""
    try:
        with open(caminho_pdf, 'rb') as f:
            leitor = PyPDF2.PdfReader(f)
            for i in range(min(max_paginas, len(leitor.pages))):
                page_text = leitor.pages[i].extract_text()
                if page_text:
                    texto_extraido += page_text + " "
    except Exception as e:
        print(f"  -> Erro ao ler PDF {caminho_pdf}: {e}")
    return texto_extraido


def extrair_resumo_limpo(texto):
    """Extrai e limpa o resumo/abstract de um texto acadêmico extraído de PDF.
    
    Remove cabeçalhos institucionais, afiliações e identifica as seções
    de resumo/abstract para retornar apenas o conteúdo relevante.
    
    Args:
        texto: Texto bruto extraído do PDF.
        
    Returns:
        String com o resumo limpo (máx. 1500 caracteres).
    """
    # Substitui múltiplas quebras e espaçamentos por espaço simples
    texto_limpo = re.sub(r'\s+', ' ', texto).strip()

    # Procura pelas divisões comuns do resumo
    inicio_match = re.search(r'(?i)\b(resumo|abstract|resumen)\b', texto_limpo)
    if not inicio_match:
        # Tenta remover cabeçalho identificando afiliações próximas do início (primeiros 500 caracteres)
        cabeçalho_idx = -1
        termos_cabeçalho = ["universidade", "university", "departamento", "department", "@", "instituto", "issn", "vol."]
        for termo in termos_cabeçalho:
            idx = texto_limpo.lower().find(termo)
            if idx != -1 and idx < 500:
                if cabeçalho_idx == -1 or idx > cabeçalho_idx:
                    cabeçalho_idx = idx

        if cabeçalho_idx != -1:
            # Encontra o fim da frase de afiliação (ponto final) ou próximo espaço longo
            fim_afiliacao = texto_limpo.find(".", cabeçalho_idx)
            if fim_afiliacao != -1 and fim_afiliacao < 600:
                texto_limpo = texto_limpo[fim_afiliacao + 1:].strip()
            else:
                espaco_pos = texto_limpo.find(" ", cabeçalho_idx)
                if espaco_pos != -1:
                    texto_limpo = texto_limpo[espaco_pos:].strip()
        return texto_limpo[:1500].strip()

    inicio_idx = inicio_match.end()

    # Procura pelo fim do resumo (início de palavras-chave ou introdução)
    fim_match = re.search(
        r'(?i)\b(keywords|palavras-chave|introducao|introdução|introduccion|introduction|material|metodos)\b',
        texto_limpo[inicio_idx:]
    )

    if fim_match:
        fim_idx = inicio_idx + fim_match.start()
        resumo_bruto = texto_limpo[inicio_idx:fim_idx].strip()
    else:
        resumo_bruto = texto_limpo[inicio_idx:inicio_idx + 1500].strip()

    # Remove eventuais caracteres de ligação como dois-pontos, traços ou pontos no início do resumo
    resumo_bruto = re.sub(r'^[\s\.\:\-\–\—\=\+]+', '', resumo_bruto)
    return resumo_bruto.strip()


def gerar_capa_pdf(caminho_pdf_entrada, caminho_capa_destino, escala=1.5):
    """Gera uma imagem PNG da primeira página do PDF como miniatura.
    
    Args:
        caminho_pdf_entrada: Caminho do PDF de entrada.
        caminho_capa_destino: Caminho de destino para a imagem PNG.
        escala: Fator de escala para a resolução da imagem (padrão: 1.5).
        
    Returns:
        True se a capa foi gerada com sucesso, False caso contrário.
    """
    try:
        with fitz.open(caminho_pdf_entrada) as pdf_doc:
            pagina_capa = pdf_doc.load_page(0)
            pix = pagina_capa.get_pixmap(matrix=fitz.Matrix(escala, escala))
            pix.save(caminho_capa_destino)
        return True
    except Exception as e:
        print(f"  -> Erro ao gerar capa do PDF: {e}")
        return False
