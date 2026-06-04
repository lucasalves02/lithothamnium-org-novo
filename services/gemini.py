import time
import re
import json
import requests


# Lista centralizada de culturas válidas para o classificador
CULTURAS_VALIDAS = [
    "cafe", "pastagens", "soja_milho", "cana", "frutiferas",
    "hortalicas", "algodao", "silvicultura", "arroz", "trigo",
    "citros", "pecuaria", "geral"
]


def gerar_sintese_e_cultura_gemini(texto_pdf, api_key):
    """Gera uma síntese prática e classifica a cultura do artigo via Gemini API.
    
    Faz uma única chamada à API do Gemini usando JSON mode para retornar
    tanto a síntese quanto a cultura detectada em formato estruturado.
    
    Args:
        texto_pdf: Texto extraído do PDF do artigo científico.
        api_key: Chave de API do Gemini.
        
    Returns:
        Dicionário com chaves 'sintese' (str) e 'cultura' (str),
        ou None em caso de falha completa.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    culturas_formatadas = ", ".join(CULTURAS_VALIDAS)

    prompt = (
        "Você é um Engenheiro Agrônomo especialista em Lithothamnium e nutrição de solos.\n"
        "Com base no texto técnico extraído do artigo científico fornecido abaixo, realize DUAS tarefas:\n\n"
        "=== TAREFA 1: SÍNTESE PRÁTICA ===\n"
        "Escreva um resumo prático especialmente direcionado a produtores rurais e agricultores brasileiros.\n\n"
        "Regras obrigatórias para a síntese:\n"
        "1. Escreva de forma fluida, simples e sem jargões acadêmicos. "
        "Substitua palavras científicas por equivalentes simples do campo (ex: 'estresse hídrico' por 'falta de água', "
        "'desenvolvimento radicular' por 'crescimento de raízes', 'adsorção de fósforo' por 'bloqueio do fósforo', "
        "'emergência' por 'nascimento de plantas', 'calagem' por 'correção de terra', 'microbiota' por 'vida biológica do solo').\n"
        "2. Evite repetir fórmulas científicas ou citações acadêmicas. Foque nos resultados: o que a pesquisa provou na prática "
        "(ex: aumento no peso das plantas, doçura do fruto, resistência a secas, raízes maiores e mais vigorosas).\n"
        "3. O resumo deve ter no máximo 300 palavras.\n"
        "4. Escreva em tom otimista, prático e instrutivo.\n"
        "5. Organize o texto para facilitar a leitura rápida por agricultores:\n"
        "   - Use parágrafos curtos e espaçados (de 2 a 3 parágrafos).\n"
        "   - Use tópicos (bullet points começando com '-') para destacar os principais resultados ou recomendações práticas.\n"
        "   - Use negrito (**exemplo**) nas palavras-chave mais importantes (como dosagens, resultados ou culturas).\n"
        "6. Comece diretamente com as descobertas e recomendações práticas. NÃO use saudações, apresentações ou fórmulas introdutórias.\n\n"
        "=== TAREFA 2: CLASSIFICAÇÃO DE CULTURA ===\n"
        f"Classifique o artigo em UMA das seguintes categorias de cultura agrícola: {culturas_formatadas}\n"
        "Escolha a categoria mais relevante com base no conteúdo do artigo. "
        "Use 'geral' apenas se o artigo não se encaixar claramente em nenhuma cultura específica.\n\n"
        f"Texto do Artigo:\n{texto_pdf}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 800,
            "temperature": 0.3,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "sintese": {
                        "type": "STRING",
                        "description": "Síntese prática do artigo para agricultores, formatada em markdown."
                    },
                    "cultura": {
                        "type": "STRING",
                        "description": "Categoria da cultura agrícola do artigo.",
                        "enum": CULTURAS_VALIDAS
                    }
                },
                "required": ["sintese", "cultura"]
            }
        }
    }

    for tentativa in range(1, 5):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=35)
            if response.status_code == 200:
                res_json = response.json()
                texto_resposta = res_json['candidates'][0]['content']['parts'][0]['text']
                resultado = json.loads(texto_resposta)

                # Validação: garante que a cultura retornada é válida
                if resultado.get("cultura") not in CULTURAS_VALIDAS:
                    resultado["cultura"] = "geral"

                return resultado
            elif response.status_code == 429:
                print(f"      [Aviso] Limite de requisições atingido (429) na tentativa {tentativa}/4. Aguardando 60 segundos...")
                time.sleep(60)
            else:
                print(f"      [Aviso] Gemini respondeu com status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"      [Erro] Conexão com Gemini falhou na tentativa {tentativa}/4: {e}")
            if tentativa < 4:
                print("      Aguardando 10 segundos antes de tentar novamente...")
                time.sleep(10)
            else:
                return None
    return None


def formatar_sintese_para_html(texto):
    """Converte texto em markdown (negritos, listas) para HTML inline.
    
    Args:
        texto: Texto da síntese com marcações markdown.
        
    Returns:
        String HTML formatada.
    """
    if not texto:
        return ""

    # Substitui marcações de negrito do markdown (**texto**) por tags html (<strong>texto</strong>)
    texto_processado = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texto)

    linhas = texto_processado.strip().split('\n')
    html_parts = []
    in_list = False

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # Se for um item de lista (começa com - ou * ou bullet)
        match_list = re.match(r'^[\-\*\u2022]\s+(.*)', linha)
        if match_list:
            if not in_list:
                html_parts.append('<ul class="list-disc pl-5 space-y-1" style="list-style-type: disc; padding-left: 1.5rem; margin-top: 0.5rem; margin-bottom: 0.75rem; color: #4a5568;">')
                in_list = True
            html_parts.append(f'<li style="margin-bottom: 0.25rem;">{match_list.group(1)}</li>')
        else:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<p style="margin-bottom: 0.75rem; line-height: 1.7;">{linha}</p>')

    if in_list:
        html_parts.append('</ul>')

    return '\n'.join(html_parts)


def limpar_para_resumo_excerpt(texto):
    """Remove formatação markdown e trunca o texto para uso como resumo curto.
    
    Args:
        texto: Texto da síntese com marcações markdown.
        
    Returns:
        String limpa com no máximo 280 caracteres.
    """
    if not texto:
        return ""
    # Remove negritos (**texto**) e asteriscos simples
    texto_limpo = re.sub(r'\*\*(.*?)\*\*', r'\1', texto)
    texto_limpo = re.sub(r'\*+', '', texto_limpo)

    linhas = texto_limpo.split('\n')
    linhas_limpas = []
    for l in linhas:
        l = l.strip()
        if not l:
            continue
        # Remove marcadores de lista no início da linha
        l = re.sub(r'^[\-\*\u2022]\s+', '', l)
        linhas_limpas.append(l)

    resultado = " ".join(linhas_limpas)
    if len(resultado) > 280:
        return resultado[:277].strip() + "..."
    return resultado
