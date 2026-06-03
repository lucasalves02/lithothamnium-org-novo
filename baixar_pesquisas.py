import os
import sys
import time
import re
import urllib.parse
import sqlite3
import unicodedata
import argparse
import requests

# Configurações de diretórios
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_ARTIGOS = os.path.join(DIRETORIO_ATUAL, 'artigos')
PASTA_ESTATICA_PDFS = os.path.join(DIRETORIO_ATUAL, 'static', 'pdfs')

# Garantir que as pastas existam
os.makedirs(PASTA_ARTIGOS, exist_ok=True)
os.makedirs(PASTA_ESTATICA_PDFS, exist_ok=True)

# Função para sanitizar o título e gerar um nome de arquivo seguro
def sanitizar_nome_arquivo(titulo):
    # Remove tags HTML ou XML como <i>, </i>, &lt;i&gt; etc.
    titulo_limpo = re.sub(r'<[^>]+>', '', titulo)
    # Remove acentos
    nfd_form = unicodedata.normalize('NFD', titulo_limpo)
    titulo_sem_acentos = "".join([c for c in nfd_form if unicodedata.category(c) != 'Mn'])
    # Remove caracteres especiais e substitui por underscore
    nome_limpo = re.sub(r'[^a-zA-Z0-9]', '_', titulo_sem_acentos.strip().lower())
    # Remove múltiplos underscores consecutivos
    nome_limpo = re.sub(r'_{2,}', '_', nome_limpo)
    # Limita tamanho do nome
    return nome_limpo[:100].strip('_') + ".pdf"

# Função para buscar títulos já cadastrados no banco SQLite
def obter_titulos_cadastrados():
    db_path = os.path.join(DIRETORIO_ATUAL, 'pesquisas.db')
    titulos = set()
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT titulo FROM pesquisas")
            for row in cursor.fetchall():
                tit = row[0].strip().lower()
                nfd = unicodedata.normalize('NFD', tit)
                tit_limpo = "".join([c for c in nfd if unicodedata.category(c) != 'Mn'])
                tit_limpo = re.sub(r'[^a-z0-9]', '', tit_limpo)
                titulos.add(tit_limpo)
            conn.close()
        except Exception as e:
            print(f"[Aviso] Erro ao consultar pesquisas.db para duplicatas: {e}")
    return titulos

# Função de busca e download usando OpenAlex
def baixar_artigos_agricolas(limite=10):
    print("=====================================================================")
    print("  Coleta Automatizada de Artigos Agrícolas (OpenAlex) - Lithothamnium")
    print("=====================================================================")
    
    # 1. Carregar títulos existentes para evitar re-download
    titulos_cadastrados = obter_titulos_cadastrados()
    print(f"-> Encontrados {len(titulos_cadastrados)} títulos cadastrados no banco pesquisas.db.")
    
    # 2. Consultar o OpenAlex para pesquisas sobre Lithothamnium/Lithothamnion
    query = "Lithothamnium"
    url_api = f"https://api.openalex.org/works?search={query}&per_page=100"
    
    # Cabeçalho User-Agent recomendado pela OpenAlex (Politeness Policy)
    headers = {
        "User-Agent": "mailto:editor@lithothamnium.org (Lithothamnium Agricultural Portal Builder)"
    }
    
    print(f"-> Buscando pesquisas em OpenAlex...")
    try:
        response = requests.get(url_api, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[Erro] Falha ao consultar o OpenAlex: {e}")
        return
        
    results = data.get("results", [])
    print(f"-> Encontrados {len(results)} artigos candidatos iniciais.")
    
    # Palavras-chave agronômicas obrigatórias (no título ou resumo)
    agri_keywords = [
        "soil", "plant", "fertilizer", "crop", "agronomy", "pasture", "cultivo", 
        "produtividade", "liming", "acidez", "adubação", "semente", "seed", 
        "agriculture", "ph", "calcium", "magnesium", "growth", "yield", 
        "mamoeiro", "cafe", "milho", "soja", "tomate", "rabanete", "melancia", 
        "fruticultura", "hortaliça", "nutrição", "vinhaça", "forrageira"
    ]
    # Termos médicos a excluir
    exclude_keywords = [
        "clinical", "medical", "dental", "dentistry", "human", "patient", "surgery", 
        "cancer", "tumor", "rats", "mice", "bone", "in vivo", "toxicity", "cell line",
        "cadmium removal", "heavy metal", "wastewater"
    ]
    
    downloads_realizados = 0
    
    for artigo in results:
        if downloads_realizados >= limite:
            break
            
        titulo = artigo.get("title", "")
        if not titulo:
            continue
            
        # Obter a melhor localização de acesso aberto com PDF
        best_location = artigo.get("best_oa_location")
        if not best_location:
            best_location = artigo.get("open_access", {})
            
        pdf_url = best_location.get("pdf_url") or best_location.get("oa_url")
        is_oa = artigo.get("open_access", {}).get("is_oa", False)
        
        # 1. Verificar se é Acesso Aberto e possui link de PDF
        if not is_oa or not pdf_url:
            continue
            
        # 2. Reconstrói o abstract se disponível
        abstract = ""
        abstract_inverted = artigo.get("abstract_inverted_index")
        if abstract_inverted:
            try:
                words = {}
                for word, pos_list in abstract_inverted.items():
                    for pos in pos_list:
                        words[pos] = word
                abstract = " ".join([words[pos] for pos in sorted(words.keys())])
            except Exception:
                pass
                
        # 3. Filtrar termos agrícolas e excluir termos médicos
        texto_busca_exclusao = (titulo + " " + abstract).lower()
        has_agri = any(k in texto_busca_exclusao for k in agri_keywords)
        has_med = any(k in texto_busca_exclusao for k in exclude_keywords)
        
        if not has_agri or has_med:
            # Exibe os pulados devido ao escopo
            # print(f"  [Escopo Inadequado] '{titulo[:50]}...'")
            continue
            
        # 4. Checagem de títulos duplicados contra o banco pesquisas.db
        tit_normalizado = titulo.strip().lower()
        nfd_tit = unicodedata.normalize('NFD', tit_normalizado)
        tit_comparacao = "".join([c for c in nfd_tit if unicodedata.category(c) != 'Mn'])
        tit_comparacao = re.sub(r'[^a-z0-9]', '', tit_comparacao)
        
        if tit_comparacao in titulos_cadastrados:
            print(f"  [Ignorado - Já no Banco pesquisas.db] '{titulo[:60]}...'")
            continue
            
        # 5. Checagem de arquivo físico duplicado no diretório
        nome_arquivo = sanitizar_nome_arquivo(titulo)
        caminho_artigos = os.path.join(PASTA_ARTIGOS, nome_arquivo)
        caminho_estatica = os.path.join(PASTA_ESTATICA_PDFS, nome_arquivo)
        
        if os.path.exists(caminho_artigos) or os.path.exists(caminho_estatica):
            print(f"  [Ignorado - Arquivo PDF já existe] '{nome_arquivo}'")
            titulos_cadastrados.add(tit_comparacao)
            continue
            
        # 6. Baixar o PDF da fonte aberta (SciELO, MDPI, etc.)
        print(f"-> Baixando ({downloads_realizados + 1}/{limite}): '{titulo[:50]}...'")
        
        try:
            time.sleep(2.0) # Atraso amigável para evitar rate limits nos repositórios
            headers_pdf = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            pdf_response = requests.get(pdf_url, headers=headers_pdf, stream=True, timeout=30)
            
            # Alguns servidores retornam 200 mas entregam um HTML de verificação de cookie.
            content_type = pdf_response.headers.get('content-type', '').lower()
            
            if pdf_response.status_code == 200 and ('pdf' in content_type or len(pdf_response.content) > 10000):
                # Caso o content-type não diga PDF mas os bytes iniciais sim
                # Salva temporariamente para verificar
                with open(caminho_artigos, 'wb') as pdf_file:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        if chunk:
                            pdf_file.write(chunk)
                
                # Validação rápida de cabeçalho PDF
                with open(caminho_artigos, 'rb') as check_file:
                    header = check_file.read(5)
                    
                if header.startswith(b"%PDF"):
                    print(f"  [Sucesso] Salvo em: artigos/{nome_arquivo}")
                    downloads_realizados += 1
                    titulos_cadastrados.add(tit_comparacao)
                else:
                    print(f"  [Aviso] Download concluído, mas o arquivo não possui cabeçalho PDF válido. Removendo.")
                    os.remove(caminho_artigos)
            else:
                print(f"  [Falha] URL não entregou um arquivo PDF (Status: {pdf_response.status_code}, Content-Type: {content_type})")
        except Exception as e:
            print(f"  [Erro] Falha ao baixar PDF: {e}")
            if os.path.exists(caminho_artigos):
                os.remove(caminho_artigos)
                
    print(f"\n=====================================================================")
    print(f"  Coleta concluída! {downloads_realizados} novos PDFs agrícolas salvos.")
    if downloads_realizados > 0:
        print("  Iniciando processamento automático dos novos artigos com newscrap.py...")
        import subprocess
        try:
            # Invoca o script newscrap.py
            subprocess.run([sys.executable, os.path.join(DIRETORIO_ATUAL, "newscrap.py")], check=True)
            print("  Processamento automático concluído com sucesso!")
        except Exception as e:
            print(f"  [Erro] Falha ao executar o newscrap.py automaticamente: {e}")
            print("  Por favor, execute manualmente: python newscrap.py")
    else:
        print("  Nenhum novo artigo foi baixado. O banco de dados já está atualizado.")
    print("=====================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de PDFs Científicos sobre Lithothamnium via OpenAlex.")
    parser.add_argument("--limit", type=int, default=10, help="Limite de PDFs para baixar (Padrão: 10)")
    args = parser.parse_args()
    
    baixar_artigos_agricolas(limite=args.limit)
