import sqlite3
from datetime import datetime
import os
import time
import shutil
import PyPDF2
from deep_translator import GoogleTranslator
import re
import fitz  # PyMuPDF
import unicodedata
import requests

# 1. Configurar o Banco de Dados (SQLite)
def configurar_banco_de_dados():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(diretorio_atual, 'pesquisas.db')
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Tabela de pesquisas científicas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pesquisas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            autores TEXT,
            resumo TEXT,
            conteudo TEXT,
            link_original TEXT UNIQUE,
            data_coleta TEXT,
            imagem TEXT,
            cultura TEXT
        )
    ''')
    
    # Tabela de postagens diárias do blog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            resumo TEXT,
            conteudo TEXT,
            autor TEXT,
            data_publicacao TEXT,
            imagem TEXT,
            cultura TEXT
        )
    ''')
    
    # Tabela de informações sobre as culturas (guia técnico)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS culturas (
            slug TEXT PRIMARY KEY,
            nome TEXT,
            resumo TEXT,
            aplicacao TEXT,
            resultados TEXT,
            imagem TEXT,
            icone TEXT
        )
    ''')
    
    conn.commit()
    return conn

# 2. Semear tabelas de culturas e blog_posts
def semear_banco(conn):
    cursor = conn.cursor()
    
    # Culturas que usam Lithothamnium
    culturas_seed = [
        {
            "slug": "cafe",
            "nome": "Café",
            "resumo": "O uso do Lithothamnium na cafeicultura potencializa o enraizamento, melhora a qualidade da bebida e aumenta a eficiência de absorção do fósforo e micronutrientes em solos ácidos.",
            "aplicacao": "<ul><li><strong>Implantação:</strong> Misturar 150g a 200g por cova com a terra de enchimento para estimular o enraizamento inicial das mudas.</li><li><strong>Lavoura Produzindo:</strong> Aplicação de 400 kg a 600 kg/ha no final da colheita ou início do período chuvoso, em faixa na projeção da copa.</li><li><strong>Foliar:</strong> Uso de formulações micronizadas de 0,5% a 1,0% na calda de pulverização durante o florescimento e pegamento (chumbinho) para evitar abortamento.</li></ul>",
            "resultados": "<ul><li>Aumento significativo no teor de cálcio e magnésio foliar, atenuando a bienalidade produtiva do café.</li><li>Melhoria na qualidade física do grão e atributos sensoriais da bebida devido ao aporte equilibrado de micronutrientes.</li><li>Desbloqueio de fósforo fixado nos solos argilosos de cafezais, promovendo maior eficiência da adubação tradicional.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1447933601403-0c6688de566e?auto=format&fit=crop&w=800&q=80",
            "icone": "coffee"
        },
        {
            "slug": "pastagens",
            "nome": "Pastagens",
            "resumo": "Fornece cálcio e magnésio de altíssima reatividade em aplicações superficiais, neutralizando o alumínio tóxico nas camadas superficiais e estimulando a rebrota rápida da gramínea.",
            "aplicacao": "<ul><li><strong>Manutenção de Pastos:</strong> Aplicação a lanço na dose de 300 kg a 500 kg/ha. Por ter alta porosidade, possui rápida reatividade sem necessidade de incorporação profunda imediata.</li><li><strong>Nutrição de Cocho:</strong> Utilizado também como aditivo tamponante em rações e sal mineral (15g a 30g por animal/dia) para equilibrar o pH ruminal.</li></ul>",
            "resultados": "<ul><li>Aumento acentuado na produção de matéria seca (biomassa foliar) e redução no tempo de rebrota após o pastejo.</li><li>Maior teor proteico na forragem e melhor aproveitamento do nitrogênio do solo.</li><li>Na nutrição animal, atua como prebiótico natural, reduzindo a incidência de acidose ruminal e elevando a conversão alimentar.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1500595046743-cd271d694d30?auto=format&fit=crop&w=800&q=80",
            "icone": "sprout"
        },
        {
            "slug": "soja_milho",
            "nome": "Soja e Milho",
            "resumo": "Essencial para o recobrimento de sementes e nutrição inicial. Garante arranque vigoroso e tolerância de plântulas a veranicos devido ao maior desenvolvimento do sistema radicular.",
            "aplicacao": "<ul><li><strong>Tratamento de Sementes (Coating):</strong> 2g a 4g de pó ultrafino por kg de semente para aceleração da emergência e proteção biológica.</li><li><strong>Sulco de Plantio:</strong> 150 kg a 250 kg/ha aplicados diretamente no sulco misturado ao adubo formulado tradicional para proteção contra a fixação de fósforo.</li></ul>",
            "resultados": "<ul><li>Proteção das sementes contra estresse osmótico e emergência mais homogênea no campo.</li><li>Aumento de 8% a 15% na massa de raízes profundas, captando água em camadas mais profundas.</li><li>Nódulos de fixação de nitrogênio maiores e mais ativos na soja devido ao fornecimento de molibdênio e cálcio bioacessível.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=800&q=80",
            "icone": "wheat"
        },
        {
            "slug": "cana",
            "nome": "Cana-de-Açúcar",
            "resumo": "Otimiza o aproveitamento da vinhaça, estimula a atividade de microrganismos nitrificadores e melhora o enraizamento das soqueiras de cana.",
            "aplicacao": "<ul><li><strong>Plantio de Cana-Planta:</strong> 300 kg a 500 kg/ha no fundo do sulco sobre os rebolos.</li><li><strong>Cana-Soqueira:</strong> Aplicação de 400 kg/ha sobre a linha da cana pós-colheita, idealmente combinado com adubação orgânica (torta de filtro e vinhaça).</li></ul>",
            "resultados": "<ul><li>Aumento nos níveis de ATR (Açúcar Total Recuperável) por tonelada de cana produzida.</li><li>Revitalização da biologia do solo sob efeito da vinhaça, atenuando a acidez extrema localizada.</li><li>Maior longevidade do canavial, estendendo o ciclo produtivo para mais cortes (soqueiras mais vigorosas).</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1631577159151-cc4085fb4cf7?auto=format&fit=crop&w=800&q=80",
            "icone": "activity"
        },
        {
            "slug": "frutiferas",
            "nome": "Frutíferas",
            "resumo": "Fornece cálcio orgânico estrutural de rápida assimilação, essencial para a firmeza da casca, redução de distúrbios fisiológicos e aumento do tempo de prateleira (shelf-life).",
            "aplicacao": "<ul><li><strong>Implantação de Pomares:</strong> Incorporar 200g a 300g por cova antes do plantio.</li><li><strong>Adubação Anual:</strong> 1,5 kg a 3 kg por planta na projeção da copa, dependendo da idade e cultura.</li><li><strong>Pulverização Foliar:</strong> Aplicação pré-colheita para prevenir distúrbios (ex: bitter pit em maçã e podridão apical em frutos).</li></ul>",
            "resultados": "<ul><li>Frutos mais firmes, resistentes ao transporte e com menor incidência de podridão na pós-colheita.</li><li>Aumento no teor de sólidos solúveis totais (Grau Brix), tornando os frutos mais doces e saborosos.</li><li>Equilíbrio hormonal que evita o abortamento de flores e queda precoce de frutos.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=800&q=80",
            "icone": "apple"
        },
        {
            "slug": "hortalicas",
            "nome": "Hortaliças",
            "resumo": "Ideal para folhosas, bulbos e frutos de ciclo rápido, fornecendo minerais solúveis que sustentam o crescimento acelerado e ativam a imunidade natural contra pragas.",
            "aplicacao": "<ul><li><strong>Preparo de Canteiros:</strong> Incorporar 50g a 100g por metro quadrado 10 dias antes do transplante das mudas.</li><li><strong>Fertirrigação:</strong> Suspensões ultrafinas (micronizadas) aplicadas a 0,2% na água de irrigação periodicamente.</li></ul>",
            "resultados": "<ul><li>Ciclo de colheita encurtado com maior peso de maços (hortaliças folhosas).</li><li>Redução na queima de bordas (tip burn) em alface devido à rápida translocação de cálcio.</li><li>Excelente compatibilidade com sistemas de cultivo orgânico certificado, servindo de base mineral limpa.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1772881382620-04ee08835ef9?auto=format&fit=crop&w=800&q=80",
            "icone": "carrot"
        },
        {
            "slug": "geral",
            "nome": "Geral",
            "resumo": "Aplicações de caráter corretivo, prebiótico e pesquisas básicas sobre os minerais do Lithothamnium no condicionamento biológico geral do ecossistema solo-planta.",
            "aplicacao": "<ul><li><strong>Condicionamento Geral:</strong> Aplicação a lanço de 300 kg a 600 kg/ha no preparo do solo ou manutenção da fertilidade geral.</li></ul>",
            "resultados": "<ul><li>Elevação rápida do pH do solo sem provocar supercalagem localizada.</li><li>Estímulo geral de bactérias nitrificadoras e redução de patógenos radiculares por indução de resistência.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1550159930-40066082a4fc?auto=format&fit=crop&w=800&q=80",
            "icone": "leaf"
        }
    ]
    
    for c in culturas_seed:
        cursor.execute('SELECT COUNT(*) FROM culturas WHERE slug = ?', (c["slug"],))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO culturas (slug, nome, resumo, aplicacao, resultados, imagem, icone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (c["slug"], c["nome"], c["resumo"], c["aplicacao"], c["resultados"], c["imagem"], c["icone"]))
        
    # Seed de posts de blog focando na crise global do fósforo e fertilizantes
    blog_seed = [
        {
            "titulo": "A Crise do Fósforo e o Gargalo do Ácido Sulfúrico na Agricultura",
            "resumo": "Com a escassez global de ácido sulfúrico e a redução na produção de superfosfatos, otimizar as fontes de fósforo no solo tornou-se uma questão de sobrevivência econômica.",
            "conteudo": """O fósforo (P) é um nutriente essencial e o principal limitante para a produtividade da agricultura em solos tropicais. Historicamente, a indústria química respondeu a essa demanda solubilizando rochas fosfáticas com ácido sulfúrico para criar fertilizantes de alta solubilidade, como o Superfosfato Simples (SFS) e o Superfosfato Triplo (SFT). <br><br>
            No entanto, a agricultura mundial enfrenta hoje um gargalo dramático: a <strong>escassez aguda e o encarecimento do ácido sulfúrico</strong>. Utilizado em múltiplos setores industriais e na refinação, o ácido sulfúrico tem tido sua produção reduzida, gerando uma reação em cadeia que diminui a produção de fósforo processado no mundo e eleva os preços históricos dos fertilizantes químicos solúveis.
            <br><br>
            Nesse cenário desafiador, o <strong>Lithothamnium</strong> surge como um aliado indispensável. Devido à sua altíssima microporosidade (área de contato biológica ativa) e riqueza de cálcio e magnésio orgânicos solúveis, a aplicação localizada de Lithothamnium cria um microambiente alcalinizante ao redor da rizosfera. Isso impede quimicamente que o fósforo seja fixado (adsorvido) pelos óxidos de ferro e alumínio do solo, otimizando a eficiência das adubações e permitindo que o produtor colha altas produtividades com menor dosagem de fósforo solúvel comercial.""",
            "autor": "Redação Lithothamnium.org",
            "data_publicacao": "03/06/2026",
            "imagem": "https://images.unsplash.com/photo-1628487749130-2d41acb1802a?auto=format&fit=crop&w=800&q=80",
            "cultura": "geral"
        },
        {
            "titulo": "Geopolítica dos Fertilizantes: A Vulnerabilidade do Agro Nacional e a Rota Biogênica",
            "resumo": "O Brasil importa mais de 85% dos fertilizantes NPK que consome. Conflitos geopolíticos e fretes elevados exigem o uso de recursos nacionais de alta eficiência.",
            "conteudo": """A força produtiva do agronegócio brasileiro esbarra em um calcanhar de Aquiles: a dependência externa de insumos. Mais de 85% dos adubos químicos tradicionais (nitrogênio, fósforo e potássio) utilizados no Brasil vêm de outros países, especialmente do Leste Europeu e Oriente Médio. 
            <br><br>
            Os recentes conflitos geopolíticos nessas regiões provocaram embargos, interrupções logísticas severas e disparadas nos fretes marítimos internacionais. O resultado foi um encarecimento avassalador das formulações químicas tradicionais, comprimindo as margens de lucro de produtores de soja, milho e café no Brasil.
            <br><br>
            Neste contexto, o <strong>Lithothamnium</strong> ganha status estratégico. Sendo um fertilizante biogênico natural e de origem marinha, as principais jazidas ecologicamente licenciadas estão situadas na costa brasileira. Utilizar Lithothamnium não é apenas uma decisão técnica para melhorar a estrutura do solo; é uma <strong>blindagem de segurança nacional</strong> que diminui a necessidade de insumos químicos importados, ativando as reservas de nutrientes nativos da terra e estimulando o crescimento com tecnologia puramente nacional.""",
            "autor": "Instituto do Lithothamnium",
            "data_publicacao": "02/06/2026",
            "imagem": "https://images.unsplash.com/photo-1642864835712-a9e172ceeafe?auto=format&fit=crop&w=800&q=80",
            "cultura": "geral"
        },
        {
            "titulo": "Como o Lithothamnium Desbloqueia o Fósforo Aprisionado no Solo",
            "resumo": "Mais de 80% do fósforo aplicado na agricultura tropical é adsorvido pelas argilas do solo. Descubra como a alga calcária liberta esse nutriente para as plantas.",
            "conteudo": """Um dos maiores desperdícios da agricultura brasileira ocorre sob os nossos pés. Solos de cerrado (Latossolos) possuem naturalmente altos teores de óxidos de ferro e alumínio. Quando aplicamos fertilizantes solúveis tradicionais (como MAP ou DAP), o fósforo livre na solução do solo é atraído eletrostaticamente por esses óxidos, formando ligações químicas extremamente fortes. Este fenômeno, chamado de fixação ou adsorção de fósforo, prende o nutriente nas argilas de forma insolúvel, impedindo que as raízes o absorvam. 
            <br><br>
            Estima-se que existam bilhões de dólares em fósforo inativo acumulados nos solos tropicais do Brasil devido a anos de adubações químicas recorrentes.
            <br><br>
            O <strong>Lithothamnium</strong> atua como a chave para destravar esse fósforo oculto:
            <ol class="list-decimal pl-5 space-y-2 mt-4">
                <li><strong>Competição Iônica:</strong> O cálcio e o magnésio de altíssima solubilidade biológica presentes no esqueleto da alga ocupam os sítios de ligação das argilas, liberando os ânions fosfato para a solução aquosa do solo.</li>
                <li><strong>Estímulo Biológico:</strong> A estrutura porosa das algas calcárias serve de refúgio ideal para bactérias solubilizadoras de fosfato e fungos micorrízicos benéficos. Ao se multiplicarem, esses microrganismos secretam ácidos orgânicos e fosfatases ácidas que desfazem os complexos de ferro-fósforo, nutrindo as plantas (soja, milho, cana) de forma natural e eficiente.</li>
            </ol>""",
            "autor": "Dr. Carlos Mendes, Agrônomo",
            "data_publicacao": "01/06/2026",
            "imagem": "https://images.unsplash.com/photo-1551649001-7a2482d98d05?auto=format&fit=crop&w=800&q=80",
            "cultura": "soja_milho"
        },
        {
            "titulo": "Fosfatos Naturais Reativos e Lithothamnium: Sinergia de Baixo Custo contra Adubos Químicos",
            "resumo": "Combinar rochas fosfáticas moídas com algas calcárias marinhas substitui com sucesso adubos químicos solúveis em lavouras de Café e Cana.",
            "conteudo": """Diante dos preços exorbitantes dos adubos fosfatados industriais solúveis, misturas alternativas ganham espaço no campo. Uma das combinações de maior sucesso agronômico é o uso conjunto de <strong>Fosfatos Naturais Reativos (FNR)</strong> com <strong>Lithothamnium</strong>.
            <br><br>
            Os Fosfatos Naturais são rochas de origem sedimentar (como os fosfatos de Gafsa ou Arad) que não passam pelo processo químico de acidificação industrial com ácido sulfúrico. Eles têm custo muito inferior, mas sua liberação de fósforo na forma solúvel é lenta e depende de acidez localizada e atividade biológica do solo para ocorrer.
            <br><br>
            Ao aplicar o Lithothamnium em conjunto com o FNR, ocorre uma sinergia biológica espetacular: as algas estimulam a proliferação da microbiota do solo, que secreta ácidos orgânicos fracos diretamente sobre as partículas da rocha fosfática, liberando o fósforo de forma gradual e contínua. 
            <br><br>
            Esse sistema de liberação controlada é ideal para lavouras perenes como o <strong>Café</strong> e de ciclo longo como a <strong>Cana-de-Açúcar</strong>, pois mantém um fluxo contínuo de nutrição sem perdas por fixação, garantindo maior produtividade com uma fração do custo dos fertilizantes químicos solúveis convencionais.""",
            "autor": "Redação Lithothamnium.org",
            "data_publicacao": "31/05/2026",
            "imagem": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
            "cultura": "cafe"
        },
        {
            "titulo": "Maximizando a Cafeicultura com Minerais Biogênicos em Lavouras de Alta Performance",
            "resumo": "Saiba como o fornecimento de cálcio e magnésio biogênico do Lithothamnium protege os cafeeiros contra veranicos e melhora o enraizamento.",
            "conteudo": """A cafeicultura brasileira moderna demanda precisão e alta tecnologia de solo. O cafeeiro possui um sistema radicular delicado, e qualquer desequilíbrio nutricional ou estresse hídrico no período de floração e formação de chumbinhos pode comprometer a safra inteira.
            <br><br>
            A inserção de <strong>Lithothamnium</strong> no cronograma de manejo da lavoura proporciona um fornecimento constante de cálcio (Ca) e magnésio (Mg) de altíssima absorção, além de silício e mais de 20 micronutrientes. O cálcio atua diretamente no fortalecimento da parede celular das raízes, promovendo um crescimento radicular vertical profundo.
            <br><br>
            Esse enraizamento agressivo permite que os cafeeiros acessem bolsões de umidade em camadas profundas do solo, conferindo uma resistência incomparável a veranicos e ondas intensas de calor. O silício e os micronutrientes estimulam ainda a imunidade natural contra pragas (como o bicho-mineiro) e resultam em frutos com maturação mais uniforme, garantindo grãos com maior teor de sólidos solúveis e bebida de qualidade superior.""",
            "autor": "Redação Lithothamnium.org",
            "data_publicacao": "30/05/2026",
            "imagem": "https://images.unsplash.com/photo-1447933601403-0c6688de566e?auto=format&fit=crop&w=800&q=80",
            "cultura": "cafe"
        },
        {
            "titulo": "Recuperação Rápida de Pastagens com Aplicação Superficial de Lithothamnium",
            "resumo": "Uma solução viável para reverter a degradação de pastos sem a necessidade de aração pesada e insumos nitrogenados de alto valor.",
            "conteudo": """Mais de metade das áreas de pastagens no Brasil sofrem de algum nível de degradação devido ao manejo inadequado e acidez severa do solo. A recuperação tradicional de pasto é financeiramente proibitiva para muitos pecuaristas, pois exige mecanização pesada (aração/gradagem) e altíssimas doses de adubos fosfatados químicos solúveis.
            <br><br>
            O <strong>Lithothamnium</strong> oferece uma alternativa de rápida resposta. Pela sua estrutura física microporosa derivada de algas, o material é altamente reativo e solúvel na água da chuva. Isso permite a aplicação **superficial a lanço** sem qualquer necessidade de incorporação mecânica ao solo.
            <br><br>
            A reatividade do Lithothamnium atua na camada superficial (0-10 cm), neutralizando o alumínio tóxico que queima as raízes finas da braquiária. O pasto responde em poucas semanas com rebrota rápida pós-pastejo, produção de folhas mais largas e escuras (ricas em clorofila e proteína) e melhoria na densidade da forragem. Para o pecuarista, representa um ganho direto na taxa de lotação animal por hectare e redução da dependência química convencional.""",
            "autor": "Instituto do Lithothamnium",
            "data_publicacao": "29/05/2026",
            "imagem": "https://images.unsplash.com/photo-1500595046743-cd271d694d30?auto=format&fit=crop&w=800&q=80",
            "cultura": "pastagens"
        }
    ]
    
    for post in blog_seed:
        cursor.execute('SELECT COUNT(*) FROM blog_posts WHERE titulo = ?', (post["titulo"],))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO blog_posts (titulo, resumo, conteudo, autor, data_publicacao, imagem, cultura)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (post["titulo"], post["resumo"], post["conteudo"], post["autor"], post["data_publicacao"], post["imagem"], post["cultura"]))
        
    conn.commit()
    print("Culturas e Posts do blog semeados com sucesso!")

# 3. Detectar cultura a partir da síntese (em português) e do título
def detectar_cultura(titulo, sintese):
    def remover_acentos(txt):
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    
    texto = (sintese + " " + titulo).lower()
    texto_busca = remover_acentos(texto)
    
    # Mapeamento robusto de termos em português correspondentes a cada cultura
    keywords = {
        "cafe": ["cafe", "cafezal", "cafezais", "cafeeiro", "cafeicultura", "coffee"],
        "cana": ["cana", "canavial", "canaviais", "soqueira", "vinhaça", "sugarcane"],
        "hortalicas": ["tomate", "rabanete", "pimentao", "pimentoes", "cebola", "alho", "alface", "hortalica", "hortalicas", "legume", "verdura"],
        "frutiferas": ["mamoeiro", "mamao", "melao", "meloes", "melancia", "pitaia", "frutifera", "frutiferas", "pomar", "pomares", "laranja", "limao", "uva", "fruta", "frutas"],
        "pastagens": ["pasto", "pastos", "pastagem", "pastagens", "capim", "braquiaria", "forrageira", "forrageiras", "confinamento", "gado", "boi", "novilho", "novilhos", "bovino", "bovinos", "pecuaria"],
        "soja_milho": ["soja", "milho", "feijao", "feijoeiro", "pinhao", "pinhao-manso", "semente", "sementes"]
    }
    
    scores = {cult: 0 for cult in keywords.keys()}
    for cult, words in keywords.items():
        for w in words:
            scores[cult] += len(re.findall(r'\b' + re.escape(w) + r'\b', texto_busca))
            if w in texto_busca:
                scores[cult] += 1
                
    max_score = max(scores.values())
    if max_score > 0:
        for cult, score in scores.items():
            if score == max_score:
                return cult
                
    return "geral"

# 4. Função para extrair o resumo limpo do PDF, removendo instituições e cabeçalhos
def extrair_resumo_limpo(texto):
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
    fim_match = re.search(r'(?i)\b(keywords|palavras-chave|introducao|introdução|introduccion|introduction|material|metodos)\b', texto_limpo[inicio_idx:])
    
    if fim_match:
        fim_idx = inicio_idx + fim_match.start()
        resumo_bruto = texto_limpo[inicio_idx:fim_idx].strip()
    else:
        resumo_bruto = texto_limpo[inicio_idx:inicio_idx+1500].strip()
        
    # Remove eventuais caracteres de ligação como dois-pontos, traços ou pontos no início do resumo
    resumo_bruto = re.sub(r'^[\s\.\:\-\–\—\=\+]+', '', resumo_bruto)
    return resumo_bruto.strip()


def gerar_sintese_gemini(texto_pdf, api_key):
    # Gemini API Generate Content URL (usando gemini-3.1-flash-lite como modelo rápido e com maiores limites)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Prompt rico para orientar o modelo a focar no linguajar de agricultor
    prompt = (
        "Você é um Engenheiro Agrônomo especialista em Lithothamnium e nutrição de solos.\n"
        "Com base no texto técnico extraído do artigo científico fornecido abaixo, escreva um resumo prático "
        "especialmente direcionado a produtores rurais e agricultores brasileiros.\n\n"
        "Regras obrigatórias:\n"
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
        "6. Comece diretamente com as descobertas e recomendações práticas. NÃO use saudações, apresentações ou fórmulas introdutórias (como 'Olá produtor', 'Como engenheiro agrônomo', 'Neste estudo', 'Sou especialista', etc.). Vá direto aos fatos e resultados reais.\n\n"
        f"Texto do Artigo:\n{texto_pdf}"
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": 600,
            "temperature": 0.3
        }
    }
    
    for tentativa in range(1, 5):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=35)
            if response.status_code == 200:
                res_json = response.json()
                sintese = res_json['candidates'][0]['content']['parts'][0]['text']
                # Retorna o texto da síntese preservando os marcadores de markdown
                return sintese.strip()
            elif response.status_code == 429:
                print(f"      [Aviso] Limite de requisições atingido (429) na tentativa {tentativa}/4. Aguardando 60 segundos antes de tentar novamente...")
                time.sleep(60)
            else:
                print(f"      [Aviso] Gemini respondeu com status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"      [Erro] Conexão com Gemini falhou na tentativa {tentativa}/4: {e}")
            if tentativa < 4:
                print("      Aguardando 10 segundos antes de tentar novamente após erro de conexão...")
                time.sleep(10)
            else:
                return None
    return None

def formatar_sintese_para_html(texto):
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
            
        # Se for um item de lista (começa com - ou * ou algarismo seguido de ponto)
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


# 5. Processar PDFs locais da pasta artigos
def processar_pdfs_locais(conn, api_key=None):
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Pastas de entrada e saída
    pasta_entrada = os.path.join(diretorio_atual, 'artigos')
    pasta_estatica_pdfs = os.path.join(diretorio_atual, 'static', 'pdfs')
    pasta_estatica_capas = os.path.join(diretorio_atual, 'static', 'capas')
    
    # Garante a existência das pastas
    os.makedirs(pasta_entrada, exist_ok=True)
    os.makedirs(pasta_estatica_pdfs, exist_ok=True)
    os.makedirs(pasta_estatica_capas, exist_ok=True)
    
    arquivos_pdf = [f for f in os.listdir(pasta_entrada) if f.lower().endswith('.pdf')]
    
    if not arquivos_pdf:
        print(f"Nenhum arquivo PDF encontrado na pasta: {pasta_entrada}")
        return
 
    print(f"Processando {len(arquivos_pdf)} PDFs encontrados na pasta 'artigos'...")
    
    cursor = conn.cursor()
    pesquisas_salvas = 0
 
    for arquivo in arquivos_pdf:
        # Gera nome de arquivo seguro
        nome_seguro = ''.join(c for c in unicodedata.normalize('NFD', arquivo) if unicodedata.category(c) != 'Mn')
        nome_seguro = re.sub(r'[^a-zA-Z0-9.\-]', '_', nome_seguro)
        if not nome_seguro.lower().endswith('.pdf'):
            nome_seguro += '.pdf'
 
        link_original = f"/static/pdfs/{nome_seguro}"
        
        # Verificação preventiva: não reprocessa o PDF se ele já constar na tabela de pesquisas
        cursor.execute("SELECT COUNT(*) FROM pesquisas WHERE link_original = ?", (link_original,))
        if cursor.fetchone()[0] > 0:
            print(f"  -> [Ignorado - Já Processado] '{arquivo}'")
            continue

        caminho_pdf_entrada = os.path.join(pasta_entrada, arquivo)
        caminho_pdf_destino = os.path.join(pasta_estatica_pdfs, nome_seguro)
        
        texto_extraido = ""
        
        # Extrair texto do PDF
        try:
            with open(caminho_pdf_entrada, 'rb') as f:
                leitor = PyPDF2.PdfReader(f)
                for i in range(min(2, len(leitor.pages))):
                    page_text = leitor.pages[i].extract_text()
                    if page_text:
                        texto_extraido += page_text + " "
        except Exception as e:
            print(f"  -> Erro ao ler PDF {arquivo}: {e}")
            continue
 
        if not texto_extraido or not texto_extraido.strip():
            print(f"  -> Não foi possível extrair texto do PDF '{arquivo}'. Pulando.")
            continue
 
        # 1. Extração Inteligente e Limpeza do Abstract
        resumo_limpo = extrair_resumo_limpo(texto_extraido)
        
        # 2. Traduzir o Abstract/Resumo
        try:
            resumo_traduzido = GoogleTranslator(source='auto', target='pt').translate(resumo_limpo)
        except Exception as e:
            resumo_traduzido = resumo_limpo
 
        # 3. Limpeza e Tradução do Título para o Português
        titulo_limpo_raw = arquivo[:-4].replace('_', ' ').replace('-', ' ')
        try:
            # Traduz o título original para português
            titulo_traduzido = GoogleTranslator(source='auto', target='pt').translate(titulo_limpo_raw)
        except Exception:
            titulo_traduzido = titulo_limpo_raw
            
        # Capitaliza o título traduzido de forma limpa
        titulo = " ".join([w.capitalize() for w in titulo_traduzido.strip().split()])
        
        # Autores simplificados
        autores = "Autoria listada no documento PDF original"
        if "&" in titulo_limpo_raw or "and" in titulo_limpo_raw.lower():
            autores = "Pesquisa acadêmica"
            
        link_original = f"/static/pdfs/{nome_seguro}"
        data_coleta = datetime.now().strftime("%d/%m/%Y")
 
        # 4. Gerar capa do PDF (imagem thumbnail)
        nome_base_seguro = nome_seguro[:-4]
        caminho_capa_destino = os.path.join(pasta_estatica_capas, f"{nome_base_seguro}.png")
        link_imagem = f"/static/capas/{nome_base_seguro}.png"
        
        try:
            with fitz.open(caminho_pdf_entrada) as pdf_doc:
                pagina_capa = pdf_doc.load_page(0)
                pix = pagina_capa.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                pix.save(caminho_capa_destino)
        except Exception as e:
            link_imagem = "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=600&q=80"
 
        # 5.5. Gerar síntese via Gemini API
        print(f"    [Gemini API] Gerando síntese para: {titulo[:45]}...")
        sintese_final = gerar_sintese_gemini(texto_extraido, api_key)
        if not sintese_final:
            sintese_final = resumo_traduzido
        resumo_bruto = limpar_para_resumo_excerpt(sintese_final)
        
        # 5. Detectar a cultura correspondente com base na síntese gerada (ou título)
        cultura_detectada = detectar_cultura(titulo, sintese_final)
        
        print(f"  -> {arquivo[:35]}... | Cultura: {cultura_detectada} | Sintese: {len(sintese_final)} chars")
 
        # 6. Conteúdo formatado como avaliação técnica de pesquisador
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
 
        try:
            cursor.execute('''
                INSERT INTO pesquisas (titulo, autores, resumo, conteudo, link_original, data_coleta, imagem, cultura)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (titulo, autores, resumo_bruto, conteudo_artigo, link_original, data_coleta, link_imagem, cultura_detectada))
            
            # Copia o PDF da pasta de artigos para static/pdfs
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
    parser = argparse.ArgumentParser(description="Reestruturação do banco de dados do Lithothamnium.org")
    parser.add_argument("--api-key", type=str, default=None, help="Chave de API do Gemini para gerar sínteses premium.")
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')

    print("Iniciando reestruturação do banco de dados do Lithothamnium.org...")
    banco_conn = configurar_banco_de_dados()
    semear_banco(banco_conn)
    processar_pdfs_locais(banco_conn, api_key)
    banco_conn.close()
    print("Processo concluído com sucesso!")
