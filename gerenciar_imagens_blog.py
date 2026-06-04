"""
gerenciar_imagens_blog.py - Ferramenta interativa para definir imagens do blog via Unsplash.

Lista os blog posts ativos e permite que você insira termos de busca específicos
para encontrar a imagem perfeita no Unsplash.

Uso:
    python gerenciar_imagens_blog.py
"""

import os
import sys
import sqlite3
import urllib.parse
import requests
from dotenv import load_dotenv

# Carrega variáveis do .env
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


def buscar_unsplash(query, unsplash_key):
    """Busca imagens no Unsplash e retorna as 3 primeiras opções para escolha."""
    url = f"https://api.unsplash.com/search/photos?query={urllib.parse.quote(query)}&client_id={unsplash_key}&per_page=3&orientation=landscape"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
    except Exception as e:
        print(f"   [Erro] Comunicação com Unsplash falhou: {e}")
    return []


def gerenciar_imagens():
    unsplash_key = os.environ.get('UNSPLASH_API_KEY')
    if not unsplash_key:
        print("[Erro] Chave do Unsplash (UNSPLASH_API_KEY) não configurada no arquivo .env.")
        return

    conn = obter_conexao()
    cursor = conn.cursor()

    cursor.execute("SELECT id, titulo, imagem FROM blog_posts")
    posts = cursor.fetchall()

    if not posts:
        print("Nenhum post de blog cadastrado no banco.")
        conn.close()
        return

    print("=" * 80)
    print("  GERENCIADOR INTERATIVO DE IMAGENS DO BLOG")
    print("=" * 80)
    print("  Este script permite escolher imagens personalizadas para cada post.")
    print("  Digite termos de busca em inglês (ex: 'soybean crop harvesting', 'cargo containers ship').")
    print("=" * 80)

    for post in posts:
        post_id = post["id"]
        titulo = post["titulo"]
        imagem_atual = post["imagem"] or "Nenhuma"

        print(f"\n[Post ID {post_id}]: '{titulo}'")
        print(f"Imagem atual: {imagem_atual[:80]}...")
        
        while True:
            opcao = input("Deseja alterar a imagem deste post? (s/n/pular): ").strip().lower()
            if opcao in ('n', 'pular', ''):
                print("Mantendo imagem atual.")
                break
            elif opcao == 's':
                busca = input("Digite o termo de busca em inglês para o Unsplash: ").strip()
                if not busca:
                    print("Busca cancelada. Mantendo imagem atual.")
                    break
                
                print(f"Buscando no Unsplash por '{busca}'...")
                resultados = buscar_unsplash(busca, unsplash_key)
                
                if not resultados:
                    print("Nenhum resultado encontrado. Tente outro termo.")
                    continue
                
                print("\nOpções encontradas:")
                for idx, res in enumerate(resultados):
                    desc = res.get("description") or res.get("alt_description") or "Sem descrição"
                    user = res.get("user", {}).get("name", "Desconhecido")
                    print(f"  [{idx + 1}] Autor: {user} | Descrição: {desc[:60]}...")
                
                escolha = input("\nEscolha a opção (1-3) ou 'c' para tentar outro termo: ").strip().lower()
                if escolha == 'c':
                    continue
                try:
                    escolha_idx = int(escolha) - 1
                    if 0 <= escolha_idx < len(resultados):
                        url_selecionada = resultados[escolha_idx]["urls"]["regular"]
                        cursor.execute("UPDATE blog_posts SET imagem = ? WHERE id = ?", (url_selecionada, post_id))
                        conn.commit()
                        print(f"   [Sucesso] Post {post_id} atualizado com a nova imagem!")
                        break
                    else:
                        print("Opção inválida.")
                except ValueError:
                    print("Opção inválida.")
            else:
                print("Opção inválida. Digite 's' para sim ou 'n' para não.")

    conn.close()
    print("\nAtualização de imagens concluída!")


if __name__ == "__main__":
    gerenciar_imagens()
