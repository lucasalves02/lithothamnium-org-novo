"""
ingest_pdfs.py - Script principal de ingestão de artigos PDF

Lê PDFs da pasta 'artigos/', extrai texto, traduz, gera síntese via Gemini API,
classifica a cultura agrícola e salva tudo no banco de dados SQLite.

Uso:
    python ingest_pdfs.py --api-key SUA_CHAVE_GEMINI
    # ou defina a variável de ambiente GEMINI_API_KEY
"""

import os
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()  # Carrega as variáveis do arquivo .env

from db import configurar_banco_de_dados, semear_banco
from services import gerar_sintese_e_cultura_gemini, formatar_sintese_para_html, limpar_para_resumo_excerpt
from services import traduzir_texto
from pdf_utils import extrair_texto_pdf, extrair_resumo_limpo, gerar_capa_pdf


def processar_pdfs_locais(conn, api_key=None, reprocessar_ids=None):
    """Processa todos os PDFs na pasta 'artigos/' e os insere no banco de dados.
    
    Para cada PDF:
      1. Extrai o texto das primeiras páginas
      2. Limpa e traduz o resumo/abstract
      3. Traduz o título para português
      4. Gera miniatura da primeira página
      5. Gera síntese prática + classificação de cultura via Gemini API
      6. Insere o registro no banco de dados SQLite
    """
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))

    # Pastas de entrada e saída
    pasta_entrada = os.path.join(diretorio_atual, 'artigos')
    pasta_estatica_pdfs = os.path.join(diretorio_atual, 'static', 'pdfs')
    pasta_estatica_capas = os.path.join(diretorio_atual, 'static', 'capas')

    # Garante a existência das pastas
    os.makedirs(pasta_entrada, exist_ok=True)
    os.makedirs(pasta_estatica_pdfs, exist_ok=True)
    os.makedirs(pasta_estatica_capas, exist_ok=True)

    cursor = conn.cursor()

    # Se reprocessar_ids foi fornecido, vamos primeiro obter os links originais dos IDs para podermos reprocessá-los.
    arquivos_para_reprocessar = []
    if reprocessar_ids:
        print(f"Reprocessando artigos com os IDs: {reprocessar_ids}")
        placeholders = ','.join('?' for _ in reprocessar_ids)
        cursor.execute(f"SELECT id, link_original, titulo FROM pesquisas WHERE id IN ({placeholders})", reprocessar_ids)
        linhas = cursor.fetchall()
        
        for linha in linhas:
            id_pesquisa, link_original, titulo_antigo = linha
            nome_arquivo = os.path.basename(link_original)
            # Tenta encontrar o arquivo original na pasta 'artigos' ou na pasta static
            caminho_artigos = os.path.join(pasta_entrada, nome_arquivo)
            caminho_estatica = os.path.join(pasta_estatica_pdfs, nome_arquivo)
            
            # Se não estiver em artigos/, mas estiver em static/pdfs/, copia de volta ou apenas usa de lá
            if not os.path.exists(caminho_artigos) and os.path.exists(caminho_estatica):
                shutil.copy2(caminho_estatica, caminho_artigos)
            
            if os.path.exists(caminho_artigos):
                arquivos_para_reprocessar.append(nome_arquivo)
                # Deleta o registro existente do banco para inserção limpa
                cursor.execute("DELETE FROM pesquisas WHERE id = ?", (id_pesquisa,))
                print(f"  -> Removido registro ID {id_pesquisa} ('{titulo_antigo}') para reprocessamento.")
            else:
                print(f"  [Aviso] Arquivo PDF '{nome_arquivo}' correspondente ao ID {id_pesquisa} não encontrado em 'artigos' nem em 'static/pdfs'.")
        conn.commit()

    arquivos_pdf = [f for f in os.listdir(pasta_entrada) if f.lower().endswith('.pdf')]

    # Se estamos reprocessando IDs específicos, filtramos a lista de arquivos para conter apenas eles
    if reprocessar_ids:
        arquivos_pdf = [f for f in arquivos_pdf if f in arquivos_para_reprocessar]

    if not arquivos_pdf:
        print(f"Nenhum arquivo PDF a ser processado na pasta: {pasta_entrada}")
        return

    print(f"Processando {len(arquivos_pdf)} PDFs...")

    pesquisas_salvas = 0

    for arquivo in arquivos_pdf:
        # Gera nome de arquivo seguro (sem acentos ou caracteres especiais)
        nome_seguro = ''.join(
            c for c in unicodedata.normalize('NFD', arquivo)
            if unicodedata.category(c) != 'Mn'
        )
        nome_seguro = re.sub(r'[^a-zA-Z0-9.\-]', '_', nome_seguro)
        if not nome_seguro.lower().endswith('.pdf'):
            nome_seguro += '.pdf'

        link_original = f"/static/pdfs/{nome_seguro}"

        # Verificação preventiva: não reprocessa o PDF se ele já constar na tabela (caso geral)
        cursor.execute("SELECT COUNT(*) FROM pesquisas WHERE link_original = ?", (link_original,))
        if cursor.fetchone()[0] > 0:
            print(f"  -> [Ignorado - Já Processado] '{arquivo}'")
            continue

        # Verificação de blacklist: não reprocessa PDFs que foram removidos pelo administrador
        try:
            cursor.execute("SELECT COUNT(*) FROM pesquisas_removidas WHERE link_original = ?", (link_original,))
            if cursor.fetchone()[0] > 0:
                print(f"  -> [Ignorado - Na Blacklist] '{arquivo}'")
                continue
        except sqlite3.OperationalError:
            pass  # Tabela ainda não existe

        caminho_pdf_entrada = os.path.join(pasta_entrada, arquivo)
        caminho_pdf_destino = os.path.join(pasta_estatica_pdfs, nome_seguro)

        # ── 1. Extrair texto do PDF ──
        texto_extraido = extrair_texto_pdf(caminho_pdf_entrada)

        if not texto_extraido or not texto_extraido.strip():
            print(f"  -> Não foi possível extrair texto do PDF '{arquivo}'. Pulando.")
            continue

        # ── 2. Extração inteligente e limpeza do Abstract ──
        resumo_limpo = extrair_resumo_limpo(texto_extraido)

        # ── 3. Tradução do Abstract/Resumo ──
        resumo_traduzido = traduzir_texto(resumo_limpo)

        # ── 4. Limpeza e tradução do título para o Português ──
        titulo_limpo_raw = arquivo[:-4].replace('_', ' ').replace('-', ' ')
        titulo_traduzido = traduzir_texto(titulo_limpo_raw)

        # Capitaliza o título traduzido de forma limpa
        titulo = " ".join([w.capitalize() for w in titulo_traduzido.strip().split()])

        # Autores simplificados
        autores = "Autoria listada no documento PDF original"
        if "&" in titulo_limpo_raw or "and" in titulo_limpo_raw.lower():
            autores = "Pesquisa acadêmica"

        data_coleta = datetime.now().strftime("%d/%m/%Y")

        # ── 5. Gerar capa do PDF (imagem thumbnail) ──
        nome_base_seguro = nome_seguro[:-4]
        caminho_capa_destino = os.path.join(pasta_estatica_capas, f"{nome_base_seguro}.png")
        link_imagem = f"/static/capas/{nome_base_seguro}.png"

        capa_gerada = gerar_capa_pdf(caminho_pdf_entrada, caminho_capa_destino)
        if not capa_gerada:
            link_imagem = "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=600&q=80"

        # ── 6. Gerar síntese + classificação de cultura via Gemini API ──
        print(f"    [Gemini API] Gerando síntese e classificando cultura para: {titulo[:45]}...")
        resultado_gemini = gerar_sintese_e_cultura_gemini(texto_extraido, api_key)

        if not resultado_gemini:
            print(f"    [Erro] Gemini falhou em processar o arquivo '{arquivo}'. Abortando este artigo para evitar dados incorretos.")
            continue

        sintese_final = resultado_gemini.get("sintese")
        cultura_detectada = resultado_gemini.get("cultura", "geral")

        if not sintese_final or not sintese_final.strip():
            print(f"    [Erro] Síntese vazia retornada pelo Gemini para '{arquivo}'. Abortando este artigo.")
            continue

        resumo_bruto = limpar_para_resumo_excerpt(sintese_final)

        print(f"  -> {arquivo[:35]}... | Cultura: {cultura_detectada} | Sintese: {len(sintese_final)} chars")

        # ── 7. Conteúdo formatado como avaliação técnica de pesquisador ──
        sintese_html = formatar_sintese_para_html(sintese_final)
        conteudo_artigo = f"""
        <div class="space-y-6">
            <div class="bg-green-50 border-l-4 border-green-700 p-6 rounded-r-lg shadow-sm" style="background-color: #f0f7f1; border-left-color: #1b3d22;">
                <h3 class="text-xl font-bold text-green-900 mb-3" style="color: #1b3d22; font-size: 1.25rem; font-weight:700; margin-bottom: 0.75rem;">Síntese Prática para o Agricultor</h3>
                <div class="text-gray-800 leading-relaxed text-base" style="color: #2d3748; line-height: 1.7;">
                    {sintese_html}
                </div>
            </div>
            
            <div class="prose max-w-none text-gray-700 mt-6" style="margin-top: 1.5rem;">
                <h4 class="text-lg font-bold text-gray-900 mb-3" style="color: #1b3d22; font-size: 1.15rem; font-weight:700; margin-bottom: 0.5rem;">Relevância e Aplicação Prática</h4>
                <p class="leading-relaxed" style="color: #4a5568; line-height: 1.6; margin-bottom: 1rem;">
                    Esta publicação fornece subsídios práticos sobre o uso de <em>Lithothamnium</em> e seus reflexos no desenvolvimento de plantas. O estudo analisa os efeitos na estrutura de solos e nutrição de nutrientes específicos no contexto da cultura <strong>{cultura_detectada.replace('_', '/').capitalize()}</strong>.
                </p>
                
                <h4 class="text-lg font-bold text-gray-900 mb-3 mt-6" style="color: #1b3d22; font-size: 1.15rem; font-weight:700; margin-bottom: 0.5rem; margin-top: 1.5rem;">Estrutura de Análise do Insumo</h4>
                <ul class="list-disc pl-5 space-y-2 mt-2" style="list-style-type: disc; padding-left: 1.5rem; color: #4a5568;">
                    <li><strong>Dinâmica Mineral:</strong> Fornecimento equilibrado de carbonatos biogênicos (Cálcio e Magnésio) de reatividade acelerada no solo.</li>
                    <li><strong>Ação Bioestimulante:</strong> Ativação de microrganismos de solo que auxiliam na solubilização de minerais e retenção de água.</li>
                    <li><strong>Recomendações:</strong> As dosagens práticas recomendadas constam no documento PDF completo, disponível no link de download original.</li>
                </ul>
            </div>
        </div>
        """

        # ── 8. Inserção no banco de dados ──
        try:
            cursor.execute('''
                INSERT INTO pesquisas (titulo, autores, resumo, conteudo, link_original, data_coleta, imagem, cultura)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (titulo, autores, resumo_bruto, conteudo_artigo, link_original, data_coleta, link_imagem, cultura_detectada))

            # Copia o PDF da pasta de artigos para static/pdfs (se não estiver lá)
            if not os.path.exists(caminho_pdf_destino):
                shutil.copy2(caminho_pdf_entrada, caminho_pdf_destino)

            pesquisas_salvas += 1
            print(f"    [Sucesso] Título: {titulo}")
        except sqlite3.IntegrityError:
            print(f"    [Ignorado] Já cadastrado.")
            continue
        except Exception as e:
            print(f"    [Erro] Falha ao inserir: {e}")
            continue

    conn.commit()
    print(f"\n{pesquisas_salvas} novos artigos baseados em PDFs foram cadastrados!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestão de artigos PDF para o Lithothamnium.org")
    parser.add_argument("--api-key", type=str, default=None, help="Chave de API do Gemini para gerar sínteses e classificar culturas.")
    parser.add_argument("--reprocess", type=str, default=None, help="Lista de IDs de artigos para reprocessar separados por vírgula. Ex: 23,24,25")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')

    reprocessar_ids = None
    if args.reprocess:
        try:
            reprocessar_ids = [int(x.strip()) for x in args.reprocess.split(',') if x.strip()]
        except ValueError:
            print("[Erro] Lista de IDs em --reprocess deve conter apenas números separados por vírgula.")
            exit(1)

    print("Iniciando ingestão de artigos PDF para o Lithothamnium.org...")
    banco_conn = configurar_banco_de_dados()
    semear_banco(banco_conn)
    processar_pdfs_locais(banco_conn, api_key, reprocessar_ids)
    banco_conn.close()
    print("Processo concluído com sucesso!")
