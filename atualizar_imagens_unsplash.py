"""
atualizar_imagens_unsplash.py - Script para buscar imagens altamente relevantes usando a Unsplash API.

Atualiza as imagens de todas as culturas e postagens do blog com base em termos
de busca otimizados por IA (Gemini).

Uso:
    python atualizar_imagens_unsplash.py --api-key SUA_UNSPLASH_CLIENT_ID
"""

import os
import sys
import sqlite3
import urllib.parse
import requests
import argparse
from dotenv import load_dotenv

# Carrega chaves de ambiente do .env
load_dotenv()

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, 'pesquisas.db')


def obter_conexao():
    if not os.path.exists(CAMINHO_BANCO):
        print(f"[Erro] Banco pesquisas.db não encontrado.")
        sys.exit(1)
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    return conn


def obter_imagem_unsplash(query, unsplash_key):
    """Busca uma imagem paisagem (landscape) no Unsplash e retorna a URL regular."""
    url = f"https://api.unsplash.com/search/photos?query={urllib.parse.quote(query)}&client_id={unsplash_key}&per_page=3&orientation=landscape"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                # Retorna a URL regular da primeira imagem encontrada
                return results[0].get("urls", {}).get("regular")
            else:
                print(f"   [Aviso] Nenhuma imagem encontrada no Unsplash para o termo: '{query}'")
        else:
            print(f"   [Erro] API do Unsplash retornou status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   [Erro] Falha ao comunicar com Unsplash: {e}")
    return None


def sugerir_busca_gemini(titulo, gemini_key):
    """Usa o Gemini para sugerir a melhor frase de busca em inglês no Unsplash para o post."""
    if not gemini_key:
        # Fallback simples em inglês se não houver Gemini Key
        return titulo

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        "Você é um editor de blog de agronegócio e precisa escolher a foto de capa perfeita do Unsplash para um artigo de blog.\n"
        f"O título do artigo é: '{titulo}'\n\n"
        "Com base nesse título, retorne a melhor frase de busca (apenas de 2 a 4 palavras em inglês) "
        "para encontrar uma imagem paisagem (landscape) realista e profissional sobre o tema no Unsplash.\n"
        "Exemplos:\n"
        "- Título: 'A Crise do Fósforo e o Gargalo do Ácido Sulfúrico' -> Retorno: 'dry soil agriculture'\n"
        "- Título: 'Geopolítica dos Fertilizantes' -> Retorno: 'cargo ship logistics'\n"
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


def atualizar_culturas(unsplash_key):
    """Atualiza as imagens da tabela 'culturas' com buscas predefinidas em inglês para alta relevância."""
    print("\n=== ATUALIZANDO IMAGENS DAS CULTURAS ===")
    
    # Mapeamento otimizado de termos de busca específicos para agricultura profissional
    busca_culturas = {
        "cafe": "coffee plantation agriculture farm",
        "pastagens": "pasture cattle grass field",
        "soja_milho": "soybean farm field crop",
        "cana": "sugarcane crop harvest",
        "frutiferas": "fruit orchard apple tree",
        "hortalicas": "vegetable garden organic farming",
        "algodao": "cotton field crop harvest",
        "silvicultura": "eucalyptus forest forestry",
        "arroz": "rice paddy field agriculture",
        "trigo": "wheat field golden crop",
        "citros": "orange tree grove citrus",
        "pecuaria": "livestock cows pasture grass",
        "geral": "hands holding soil agriculture fertile"
    }

    conn = obter_conexao()
    cursor = conn.cursor()

    for slug, query in busca_culturas.items():
        print(f"Buscando imagem para cultura '{slug}' (termo: '{query}')...")
        imagem_url = obter_imagem_unsplash(query, unsplash_key)
        
        if imagem_url:
            cursor.execute("UPDATE culturas SET imagem = ? WHERE slug = ?", (imagem_url, slug))
            conn.commit()
            print(f"   [Sucesso] Cultura '{slug}' atualizada com a URL: {imagem_url[:75]}...")
        else:
            print(f"   [Falha] Mantida imagem anterior para a cultura '{slug}'")

    conn.close()


def atualizar_blog_posts(unsplash_key, gemini_key):
    """Atualiza as imagens das postagens do blog usando termos sugeridos pelo Gemini."""
    print("\n=== ATUALIZANDO IMAGENS DOS POSTS DE BLOG ===")
    
    conn = obter_conexao()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, titulo FROM blog_posts")
    posts = cursor.fetchall()
    
    for post in posts:
        post_id = post["id"]
        titulo = post["titulo"]
        
        print(f"\nPost [{post_id}]: '{titulo}'")
        print("   [Gemini] Otimizando termo de busca no Unsplash...")
        termo_busca = sugerir_busca_gemini(titulo, gemini_key)
        print(f"   Termo otimizado: '{termo_busca}'")
        
        imagem_url = obter_imagem_unsplash(termo_busca, unsplash_key)
        if imagem_url:
            cursor.execute("UPDATE blog_posts SET imagem = ? WHERE id = ?", (imagem_url, post_id))
            conn.commit()
            print(f"   [Sucesso] Post [{post_id}] atualizado com a URL: {imagem_url[:75]}...")
        else:
            print(f"   [Falha] Mantida imagem anterior.")
            
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atualiza imagens do Lithothamnium.org usando a Unsplash API.")
    parser.add_argument("--api-key", type=str, default=None, help="Chave de API do Unsplash (Access Key).")
    args = parser.parse_args()

    unsplash_key = args.api_key or os.environ.get('UNSPLASH_API_KEY')
    gemini_key = os.environ.get('GEMINI_API_KEY')

    if not unsplash_key:
        print("[Erro] Chave do Unsplash não encontrada. Defina a variável UNSPLASH_API_KEY no arquivo .env ou use --api-key.")
        sys.exit(1)

    atualizar_culturas(unsplash_key)
    atualizar_blog_posts(unsplash_key, gemini_key)
    print("\nProcesso de atualização de imagens concluído com sucesso!")
