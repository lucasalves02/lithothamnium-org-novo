"""
gerar_posts_blog.py - Script para gerar e reescrever blog posts usando a Gemini API

Permite:
  1. Reescrever todos os blog posts existentes no banco de dados para torná-los profundos e profissionais.
  2. Gerar uma nova postagem a partir de um título e cultura.

Uso:
    python gerar_posts_blog.py --reescrever
    python gerar_posts_blog.py --novo "Benefícios do Lithothamnium na cultura do Milho" --cultura soja_milho
"""

import os
import sys
import sqlite3
import json
import requests
import argparse
import urllib.parse
from dotenv import load_dotenv

# Carrega chaves de API do arquivo .env
load_dotenv()

# Caminho para o banco de dados
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, 'pesquisas.db')


def obter_conexao():
    """Conecta ao banco de dados SQLite principal."""
    if not os.path.exists(CAMINHO_BANCO):
        print(f"[Erro] Banco de dados pesquisas.db não encontrado em {CAMINHO_BANCO}")
        sys.exit(1)
    
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    return conn


def obter_imagem_unsplash(query, unsplash_key):
    """Busca uma imagem no Unsplash para o termo e retorna a URL regular."""
    url = f"https://api.unsplash.com/search/photos?query={urllib.parse.quote(query)}&client_id={unsplash_key}&per_page=1&orientation=landscape"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return results[0].get("urls", {}).get("regular")
    except Exception as e:
        print(f"   [Erro Unsplash] Falha ao buscar imagem: {e}")
    return None


def sugerir_busca_gemini(titulo, gemini_key):
    """Usa o Gemini para sugerir a melhor frase de busca em inglês no Unsplash para o post."""
    if not gemini_key:
        return titulo

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        "Você é um editor de blog de agronegócio e precisa escolher a foto de capa do Unsplash para um artigo.\n"
        f"O título é: '{titulo}'\n\n"
        "Com base nesse título, retorne a melhor frase de busca (apenas de 2 a 4 palavras em inglês) "
        "para encontrar uma imagem paisagem profissional sobre o tema no Unsplash.\n"
        "Retorne APENAS a frase de busca em inglês, sem aspas, explicações ou caracteres adicionais."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 20, "temperature": 0.1}
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            resposta = res.json()['candidates'][0]['content']['parts'][0]['text']
            return resposta.strip().replace('"', '').replace("'", "")
    except Exception:
        pass
    return titulo


def chamar_gemini_para_post(titulo, resumo_atual, conteudo_atual, cultura, api_key, tipo='tecnico'):
    """Chama a API do Gemini para gerar/reescrever um post de blog com análise aprofundada."""
    # Usaremos o modelo gemini-3.1-flash-lite que é suportado na API v1beta
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    if tipo == 'tecnico':
        role_description = (
            "Você é um Engenheiro Agrônomo e Pesquisador Doutor renomado em Solos, Nutrição de Plantas e Biologia Marinha aplicada à agricultura.\n"
            "Sua tarefa é escrever um artigo técnico de blog extremamente completo, aprofundado e altamente profissional, focado na autoridade científica e relevância agronômica.\n"
        )
        style_guidelines = (
            "1. Tom e Estilo: Use um tom de autoridade técnica, profissional e científico. Deve parecer um artigo de um especialista respeitado ou pesquisador de pós-graduação.\n"
            "2. Nível de Detalhe: Evite explicações superficiais. Aprofunde-se nos processos químicos, físicos e biológicos envolvidos. "
            "Explique mecanismos específicos, como a troca iônica de cálcio e magnésio, dinâmica de absorção radicular, "
            "efeitos da porosidade do Lithothamnium no microbioma/vida biológica do solo, tamponamento de pH ruminal (se for pecuária), "
            "estruturação de paredes celulares por pectato de cálcio, resistência a nematoides, etc.\n"
        )
        badge_html = '<div class="mb-4 inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-green-100 text-green-800" style="background-color: #e6f4ea; color: #137333; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; display: inline-block; margin-bottom: 1.5rem;">Artigo Técnico Científico</div>'
    else:
        role_description = (
            "Você é um Consultor Agrícola de Campo e Agrônomo Extensionista experiente no agronegócio brasileiro.\n"
            "Sua tarefa é escrever um artigo prático de blog voltado diretamente para o agricultor/produtor rural, focado em aplicação prática, produtividade no campo, retorno sobre investimento (ROI) e soluções de manejo no dia a dia.\n"
        )
        style_guidelines = (
            "1. Tom e Estilo: Use uma linguagem acessível, direta, convincente e prática, conversando de forma próxima com o produtor rural brasileiro. Evite academicismos excessivos, mas mantenha a seriedade e o profissionalismo de uma recomendação técnica confiável.\n"
            "2. Nível de Detalhe: Foque nas recomendações práticas e no dia a dia da fazenda: como aplicar o Lithothamnium, época ideal de aplicação, dosagens recomendadas (ex: por hectare ou por planta/cova), retorno financeiro estimado, facilidade de espalhamento e o que ele vai ganhar com isso em termos práticos de colheita e lucratividade.\n"
        )
        badge_html = '<div class="mb-4 inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-blue-100 text-blue-800" style="background-color: #e8f0fe; color: #1a73e8; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; display: inline-block; margin-bottom: 1.5rem;">Guia Prático do Produtor</div>'

    prompt = (
        f"{role_description}\n"
        f"Tema/Título do Artigo: {titulo}\n"
        f"Cultura Relacionada: {cultura}\n\n"
    )

    if conteudo_atual:
        prompt += (
            "Use o conteúdo atual como guia/ponto de partida, mas reescreva-o de acordo com o público escolhido:\n"
            f"--- CONTEÚDO ATUAL INICIAL ---\n{conteudo_atual}\n-------------------------------\n\n"
        )

    prompt += (
        "Diretrizes obrigatórias para o artigo:\n"
        f"{style_guidelines}"
        "3. Estrutura e Formatação (Retorne em HTML puro pronto para renderização):\n"
        "   - Organize o texto com subtítulos claros usando tags `<h3 class=\"text-xl font-bold mt-6 mb-3\" style=\"color: #1b3d22;\">Subtítulo</h3>`.\n"
        "   - Use parágrafos claros com `<p class=\"leading-relaxed mb-4\" style=\"color: #4a5568;\">`.\n"
        "   - Use termos e tópicos em negrito `<strong>palavra-chave</strong>` para destacar conceitos fundamentais.\n"
        "   - Quando aplicável, utilize listas ordenadas `<ol>` ou não-ordenadas `<ul>` e `<li>` formatadas de maneira limpa.\n"
        "   - Comece diretamente com o texto do post, sem títulos h1/h2 repetidos no conteúdo.\n"
        "4. Extensão: O conteúdo deve ter entre 600 e 1000 palavras, garantindo uma cobertura completa e de alta densidade.\n"
        "5. Resumo Curto: Escreva também um resumo atrativo e profissional (de no máximo 200 caracteres), adequado para o card de listagem do blog.\n\n"
        "Retorne a resposta EXCLUSIVAMENTE em formato JSON com a seguinte estrutura:\n"
        "{\n"
        '  "resumo": "Resumo curto de 150-200 caracteres",\n'
        '  "conteudo": "Texto completo do artigo estruturado em HTML"\n'
        "}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.45,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            res_json = response.json()
            texto_resposta = res_json['candidates'][0]['content']['parts'][0]['text']
            resultado = json.loads(texto_resposta)
            
            # Adiciona o badge de classificação visual no início do conteúdo HTML
            if resultado.get("conteudo"):
                resultado["conteudo"] = badge_html + "\n" + resultado["conteudo"]
                
            return resultado
        else:
            print(f"      [Erro] Gemini respondeu com status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"      [Erro] Falha ao comunicar com Gemini: {e}")
        return None


def reescrever_posts_existentes(api_key, tipo='tecnico'):
    """Busca todas as postagens no banco e as reescreve com a API do Gemini."""
    conn = obter_conexao()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, titulo, resumo, conteudo, cultura FROM blog_posts")
    posts = cursor.fetchall()
    
    if not posts:
        print("Nenhum post encontrado para reescrever.")
        conn.close()
        return

    print(f"\nIniciando reescrita de {len(posts)} posts existentes no banco de dados como estilo: {tipo.upper()}...")
    
    sucessos = 0
    for post in posts:
        post_id = post["id"]
        titulo = post["titulo"]
        resumo_atual = post["resumo"]
        conteudo_atual = post["conteudo"]
        cultura = post["cultura"] or "geral"

        print(f"\n-> Reescrevendo post [{post_id}]: '{titulo}'...")
        
        resultado = chamar_gemini_para_post(titulo, resumo_atual, conteudo_atual, cultura, api_key, tipo)
        
        if resultado and resultado.get("conteudo"):
            novo_resumo = resultado.get("resumo", resumo_atual)
            novo_conteudo = resultado.get("conteudo")
            
            cursor.execute("""
                UPDATE blog_posts 
                SET resumo = ?, conteudo = ? 
                WHERE id = ?
            """, (novo_resumo, novo_conteudo, post_id))
            conn.commit()
            
            print(f"   [Sucesso] Post [{post_id}] atualizado! ({len(novo_conteudo)} caracteres)")
            sucessos += 1
        else:
            print(f"   [Falha] Não foi possível atualizar o post [{post_id}]. Mantido o conteúdo original.")
            
    conn.close()
    print(f"\nProcesso concluído! {sucessos} posts foram reescritos e aprofundados.")


def criar_novo_post(titulo, cultura, api_key, tipo='tecnico'):
    """Gera um novo post de blog sobre o título fornecido e o insere no banco de dados."""
    conn = obter_conexao()
    cursor = conn.cursor()

    # Define uma imagem genérica por cultura ou padrão
    imagens_culturas = {
        "cafe": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=800&q=80",
        "pastagens": "https://images.unsplash.com/photo-1500595046743-cd271d694d30?auto=format&fit=crop&w=800&q=80",
        "soja_milho": "https://images.unsplash.com/photo-1530595467537-0b5996c41f2d?auto=format&fit=crop&w=800&q=80",
        "cana": "https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?auto=format&fit=crop&w=800&q=80",
        "frutiferas": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=800&q=80",
        "hortalicas": "https://images.unsplash.com/photo-1566385101042-1a010c129fa6?auto=format&fit=crop&w=800&q=80",
        "pecuaria": "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?auto=format&fit=crop&w=800&q=80",
    }
    imagem = imagens_culturas.get(cultura, "https://images.unsplash.com/photo-1463121859909-073be64ff2f8?auto=format&fit=crop&w=800&q=80")
    
    # Tenta obter uma imagem dinâmica no Unsplash se a chave estiver configurada
    unsplash_key = os.environ.get('UNSPLASH_API_KEY')
    if unsplash_key:
        print("   [Unsplash] Buscando imagem dinâmica com IA para o novo post...")
        termo_busca = sugerir_busca_gemini(titulo, api_key)
        imagem_dinamica = obter_imagem_unsplash(termo_busca, unsplash_key)
        if imagem_dinamica:
            imagem = imagem_dinamica
            print(f"   [Unsplash] Imagem dinâmica selecionada: '{termo_busca}'")
    
    print(f"\nGerando novo post ({tipo}) sobre: '{titulo}'...")
    resultado = chamar_gemini_para_post(titulo, None, None, cultura, api_key, tipo)

    if resultado and resultado.get("conteudo"):
        resumo = resultado.get("resumo")
        conteudo = resultado.get("conteudo")
        autor = "Redação Lithothamnium.org"
        from datetime import datetime
        data_publicacao = datetime.now().strftime("%d/%m/%Y")

        cursor.execute("""
            INSERT INTO blog_posts (titulo, resumo, conteudo, autor, data_publicacao, imagem, cultura)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (titulo, resumo, conteudo, autor, data_publicacao, imagem, cultura))
        conn.commit()

        print(f"   [Sucesso] Novo post criado e inserido com ID {cursor.lastrowid}!")
    else:
        print("   [Falha] Não foi possível gerar o novo post.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador e reescritor de posts do blog usando a Gemini API.")
    parser.add_argument("--reescrever", action="store_true", help="Reescreve todos os posts de blog existentes.")
    parser.add_argument("--novo", type=str, default=None, help="Título do novo post de blog a ser gerado.")
    parser.add_argument("--cultura", type=str, default="geral", help="Slug da cultura relacionada para o novo post.")
    parser.add_argument("--tipo", type=str, choices=["tecnico", "produtor"], default="tecnico", help="Tipo de postagem: 'tecnico' (foco científico/químico) ou 'produtor' (guia prático de campo).")
    parser.add_argument("--api-key", type=str, default=None, help="Chave de API do Gemini.")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("[Erro] Chave de API do Gemini não informada. Defina a variável de ambiente GEMINI_API_KEY ou use --api-key.")
        sys.exit(1)

    if args.reescrever:
        reescrever_posts_existentes(api_key, args.tipo)
    elif args.novo:
        criar_novo_post(args.novo, args.cultura, api_key, args.tipo)
    else:
        parser.print_help()
