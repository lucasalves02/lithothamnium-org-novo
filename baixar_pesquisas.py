import os
import sys
import time
import re
import urllib.parse
import sqlite3
import unicodedata
import argparse
import requests
from dotenv import load_dotenv
load_dotenv()  # Carrega as variáveis do arquivo .env

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

# Função para buscar títulos já cadastrados ou removidos (blacklist) no banco SQLite
def obter_titulos_cadastrados():
    db_path = os.path.join(DIRETORIO_ATUAL, 'pesquisas.db')
    titulos = set()
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Títulos ativos no banco
            cursor.execute("SELECT titulo FROM pesquisas")
            for row in cursor.fetchall():
                tit = row[0].strip().lower()
                nfd = unicodedata.normalize('NFD', tit)
                tit_limpo = "".join([c for c in nfd if unicodedata.category(c) != 'Mn'])
                tit_limpo = re.sub(r'[^a-z0-9]', '', tit_limpo)
                titulos.add(tit_limpo)
            # Títulos removidos (blacklist) — evita re-download
            try:
                cursor.execute("SELECT titulo FROM pesquisas_removidas")
                for row in cursor.fetchall():
                    tit = row[0].strip().lower()
                    nfd = unicodedata.normalize('NFD', tit)
                    tit_limpo = "".join([c for c in nfd if unicodedata.category(c) != 'Mn'])
                    tit_limpo = re.sub(r'[^a-z0-9]', '', tit_limpo)
                    titulos.add(tit_limpo)
            except sqlite3.OperationalError:
                pass  # Tabela ainda não existe (primeira execução)
            conn.close()
        except Exception as e:
            print(f"[Aviso] Erro ao consultar pesquisas.db para duplicatas: {e}")
    return titulos

# Função de busca e download usando OpenAlex
def baixar_artigos_agricolas(limite=10, api_key=None):
    print("=====================================================================")
    print("  Coleta Automatizada de Artigos Agrícolas (OpenAlex) - Lithothamnium")
    print("=====================================================================")
    
    # 1. Carregar títulos existentes para evitar re-download
    titulos_cadastrados = obter_titulos_cadastrados()
    print(f"-> Encontrados {len(titulos_cadastrados)} títulos cadastrados no banco pesquisas.db.")
    
    # 2. Consultar o OpenAlex com busca expandida para capturar termos em português da SciELO
    query = 'Lithothamnium OR Lithothamnion OR "alga calcária" OR "algas calcárias"'
    url_api = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per_page=100"
    
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
    
    # Palavras-chave agronômicas FORTES (1 match já é suficiente para considerar relevante)
    agri_keywords_strong = [
        "fertilizer", "fertilizante", "adubação", "adubo", "adubacao",
        "crop", "lavoura", "cultivo", "plantio", "safra",
        "agronomy", "agronomia", "agronomico",
        "pasture", "pastagem", "pasto", "forrageira", "forragem",
        "liming", "calagem", "corretivo", "acidez do solo",
        "semente", "seed", "seedling", "muda", "mudas",
        "produtividade", "yield", "colheita", "harvest",
        "hortaliça", "hortalica", "fruticultura", "frutiferas",
        "cafeeiro", "cafe", "coffee",
        "milho", "corn", "maize", "soja", "soybean",
        "cana-de-acucar", "sugarcane", "cana de acucar",
        "tomate", "tomato", "rabanete", "radish", "melancia", "watermelon",
        "mamoeiro", "papaya", "mamao", "melao", "melon",
        "pimentao", "bell pepper", "alface", "lettuce",
        "algodao", "cotton", "arroz", "rice", "trigo", "wheat",
        "citros", "citrus", "laranja", "orange", "limao",
        "eucalipto", "eucalyptus", "silvicultura", "forestry",
        "vinhaça", "vinhaca", "nutrição de plantas", "plant nutrition",
        "solo agricola", "agricultural soil", "rizosfera", "rhizosphere",
        "enraizamento", "rooting", "sistema radicular", "root system",
        "confinamento", "feedlot", "bovino", "cattle", "novilho", "steer",
        "sal mineral", "mineral salt", "nutrição animal", "animal nutrition",
        "prebiotico", "prebiotic", "ruminante", "ruminant",
    ]

    # Palavras-chave agronômicas FRACAS (precisam de 2+ matches para valer)
    agri_keywords_weak = [
        "soil", "plant", "growth", "calcium", "magnesium",
        "ph", "nutrição", "nutrition", "biomass", "biomassa",
        "organic", "organico", "root", "raiz",
    ]

    # Termos de EXCLUSÃO expandidos (artigos com esses termos são descartados)
    exclude_keywords = [
        # Medicina e saúde
        "clinical", "medical", "dental", "dentistry", "human", "patient", "surgery",
        "cancer", "tumor", "rats", "mice", "bone graft", "bone substitute", "bone tissue",
        "in vivo", "toxicity", "cell line", "osteoblast", "orthopedic", "implant",
        "pharmaceutical", "drug delivery", "therapeutic",
        # Geologia / Oceanografia / Paleontologia
        "seafloor", "ocean floor", "deep sea", "marine sediment", "sedimentology",
        "geochemistry", "geoquimica", "paleontology", "paleontologia", "fossil",
        "eocene", "miocene", "pliocene", "holocene", "pleistocene", "quaternary",
        "stratigraphy", "estratigrafia", "tectonic", "volcanic",
        "continental shelf", "plataforma continental", "bathymetry",
        "reef ecology", "coral reef", "recife de coral",
        # Taxonomia / Biologia marinha pura
        "taxonomy", "taxonomia", "taxonomic", "new species", "nova especie",
        "morphological analysis", "rhodolith bed", "rhodolith",
        "coralline algae ecology", "species description", "phylogeny", "filogenia",
        "biogeography", "biogeografia", "seabed", "leito marinho",
        "crustose coralline", "crostosas", "coralinaceas",
        "sea lily", "crinoid", "echinoderm",
        # Ciência de alimentos / Industrial
        "food product", "food industry", "snack", "biscoito", "cookie", "biscuit",
        "beverage", "bebida", "consumer acceptance", "aceitação do consumidor",
        "sensory evaluation", "avaliação sensorial",
        "food additive", "aditivo alimentar", "food supplement",
        # Meio ambiente / Remediação
        "cadmium removal", "heavy metal", "wastewater", "water treatment",
        "bioremediation", "bioremediação", "pollutant", "poluente",
        "carbon sequestration in ocean", "ocean acidification",
        # Biofilme / Microbiologia pura
        "biofilm formation", "formação de biofilme", "transcriptomic",
        "transcriptômica", "gene expression profiling",
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

        # 1. Verificar se o artigo pertence à base SciELO
        locations = artigo.get("locations", []) or []
        e_scielo = False
        scielo_pdf_url = None
        
        for loc in locations:
            landing_url = (loc.get("landing_page_url") or "").lower()
            pdf_loc_url = (loc.get("pdf_url") or "").lower()
            source = loc.get("source") or {}
            source_name = (source.get("display_name") or "").lower()
            
            # Se encontrar qualquer menção a scielo na URL de pouso, PDF ou no nome da fonte
            if "scielo" in landing_url or "scielo" in pdf_loc_url or "scielo" in source_name:
                e_scielo = True
                if loc.get("pdf_url"):
                    scielo_pdf_url = loc.get("pdf_url")
                    break
        
        # Checa também se o DOI pertence à SciELO Brasil (10.1590)
        doi = (artigo.get("doi") or "").lower()
        if "10.1590" in doi:
            e_scielo = True
            
        if not e_scielo:
            continue
            
        # Se for SciELO, prioriza a URL do PDF da própria SciELO
        pdf_url = scielo_pdf_url or pdf_url

        # Verificar se é Acesso Aberto e possui link de PDF válido
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

        # 3. Filtrar termos agrícolas e excluir termos irrelevantes
        texto_busca = (titulo + " " + abstract).lower()

        # Verificação de exclusão (prioridade máxima)
        has_exclude = any(k in texto_busca for k in exclude_keywords)
        if has_exclude:
            continue

        # Verificação de relevância agrícola (sistema de pontuação)
        has_strong = any(k in texto_busca for k in agri_keywords_strong)
        weak_count = sum(1 for k in agri_keywords_weak if k in texto_busca)

        # Precisa de pelo menos 1 termo forte OU 2+ termos fracos
        if not has_strong and weak_count < 2:
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
        print("  Iniciando processamento automático dos novos artigos com ingest_pdfs.py...")
        import subprocess
        try:
            # Invoca o script ingest_pdfs.py repassando a API key
            cmd = [sys.executable, os.path.join(DIRETORIO_ATUAL, "ingest_pdfs.py")]
            if api_key:
                cmd.extend(["--api-key", api_key])
            subprocess.run(cmd, check=True)
            print("  Processamento automático concluído com sucesso!")
        except Exception as e:
            print(f"  [Erro] Falha ao executar o ingest_pdfs.py automaticamente: {e}")
            print("  Por favor, execute manualmente: python ingest_pdfs.py")
    else:
        print("  Nenhum novo artigo foi baixado. O banco de dados já está atualizado.")
    print("=====================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de PDFs Científicos sobre Lithothamnium via OpenAlex.")
    parser.add_argument("--limit", type=int, default=10, help="Limite de PDFs para baixar (Padrão: 10)")
    parser.add_argument("--api-key", type=str, default=None, help="Chave de API do Gemini para gerar sínteses e classificar culturas.")
    args = parser.parse_args()

    chave_api = args.api_key or os.environ.get('GEMINI_API_KEY')
    baixar_artigos_agricolas(limite=args.limit, api_key=chave_api)
