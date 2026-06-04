import sqlite3
import os


def configurar_banco_de_dados():
    """Cria (ou conecta) o banco de dados SQLite e garante a existência das tabelas."""
    diretorio_atual = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    # Tabela de pesquisas removidas (blacklist para evitar re-download)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pesquisas_removidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            link_original TEXT UNIQUE,
            motivo TEXT,
            data_remocao TEXT
        )
    ''')

    conn.commit()
    return conn


def semear_banco(conn):
    """Alimenta as tabelas de culturas e blog_posts com dados iniciais (seed)."""
    cursor = conn.cursor()
    # ────────────────────────────────────────────
    culturas_seed = [
        {
            "slug": "cafe",
            "nome": "Café",
            "resumo": "O uso do Lithothamnium na cafeicultura potencializa o enraizamento, melhora a qualidade da bebida e aumenta a eficiência de absorção do fósforo e micronutrientes em solos ácidos.",
            "aplicacao": "<ul><li><strong>Implantação:</strong> Misturar 150g a 200g por cova com a terra de enchimento para estimular o enraizamento inicial das mudas.</li><li><strong>Lavoura Produzindo:</strong> Aplicação de 400 kg a 600 kg/ha no final da colheita ou início do período chuvoso, em faixa na projeção da copa.</li><li><strong>Foliar:</strong> Uso de formulações micronizadas de 0,5% a 1,0% na calda de pulverização durante o florescimento e pegamento (chumbinho) para evitar abortamento.</li></ul>",
            "resultados": "<ul><li>Aumento significativo no teor de cálcio e magnésio foliar, atenuando a bienalidade produtiva do café.</li><li>Melhoria na qualidade física do grão e atributos sensoriais da bebida devido ao aporte equilibrado de micronutrientes.</li><li>Desbloqueio de fósforo fixado nos solos argilosos de cafezais, promovendo maior eficiência da adubação tradicional.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=800&q=80",
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
            "imagem": "https://images.unsplash.com/photo-1530595467537-0b5996c41f2d?auto=format&fit=crop&w=800&q=80",
            "icone": "wheat"
        },
        {
            "slug": "cana",
            "nome": "Cana-de-Açúcar",
            "resumo": "Otimiza o aproveitamento da vinhaça, estimula a atividade de microrganismos nitrificadores e melhora o enraizamento das soqueiras de cana.",
            "aplicacao": "<ul><li><strong>Plantio de Cana-Planta:</strong> 300 kg a 500 kg/ha no fundo do sulco sobre os rebolos.</li><li><strong>Cana-Soqueira:</strong> Aplicação de 400 kg/ha sobre a linha da cana pós-colheita, idealmente combinado com adubação orgânica (torta de filtro e vinhaça).</li></ul>",
            "resultados": "<ul><li>Aumento nos níveis de ATR (Açúcar Total Recuperável) por tonelada de cana produzida.</li><li>Revitalização da biologia do solo sob efeito da vinhaça, atenuando a acidez extrema localizada.</li><li>Maior longevidade do canavial, estendendo o ciclo produtivo para mais cortes (soqueiras mais vigorosas).</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?auto=format&fit=crop&w=800&q=80",
            "icone": "activity"
        },
        {
            "slug": "frutiferas",
            "nome": "Frutíferas",
            "resumo": "Fornece cálcio orgânico estrutural de rápida assimilação, essencial para a firmeza da casca, redução de distúrbios fisiológicos e aumento do tempo de prateleira (shelf-life).",
            "aplicacao": "<ul><li><strong>Implantação de Pomares:</strong> Incorporar 200g a 300g por cova antes do plantio.</li><li><strong>Adubação Anual:</strong> 1,5 kg a 3 kg por planta na projeção da copa, dependendo da idade e cultura.</li><li><strong>Pulverização Foliar:</strong> Aplicação pré-colheita para prevenir distúrbios (ex: bitter pit em maçã e podridão apical em frutos).</li></ul>",
            "resultados": "<ul><li>Frutos mais firmes, resistentes ao transporte e com menor incidência de podridão na pós-colheita.</li><li>Aumento no teor de sólidos solúveis totais (Grau Brix), tornando os frutos mais doces e saborosos.</li><li>Equilíbrio hormonal que evita o abortamento de flores e queda precoce de frutos.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=800&q=80",
            "icone": "apple"
        },
        {
            "slug": "hortalicas",
            "nome": "Hortaliças",
            "resumo": "Ideal para folhosas, bulbos e frutos de ciclo rápido, fornecendo minerais solúveis que sustentam o crescimento acelerado e ativam a imunidade natural contra pragas.",
            "aplicacao": "<ul><li><strong>Preparo de Canteiros:</strong> Incorporar 50g a 100g por metro quadrado 10 dias antes do transplante das mudas.</li><li><strong>Fertirrigação:</strong> Suspensões ultrafinas (micronizadas) aplicadas a 0,2% na água de irrigação periodicamente.</li></ul>",
            "resultados": "<ul><li>Ciclo de colheita encurtado com maior peso de maços (hortaliças folhosas).</li><li>Redução na queima de bordas (tip burn) em alface devido à rápida translocação de cálcio.</li><li>Excelente compatibilidade com sistemas de cultivo orgânico certificado, servindo de base mineral limpa.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1566385101042-1a010c129fa6?auto=format&fit=crop&w=800&q=80",
            "icone": "carrot"
        },
        # ──────────────────────────────────────────────
        # NOVAS CULTURAS
        # ──────────────────────────────────────────────
        {
            "slug": "algodao",
            "nome": "Algodão",
            "resumo": "O Lithothamnium melhora a estruturação das fibras do algodão ao fornecer cálcio e micronutrientes essenciais para a formação dos capulhos, além de aumentar a resistência das plantas a nematóides de solo.",
            "aplicacao": "<ul><li><strong>Plantio:</strong> Aplicação de 200 kg a 400 kg/ha no sulco de plantio, junto ao adubo formulado.</li><li><strong>Cobertura:</strong> 300 kg/ha em cobertura entre os estádios B1 e F1 (início do florescimento) para suprir a alta demanda de cálcio durante a formação das maçãs.</li></ul>",
            "resultados": "<ul><li>Fibras mais longas e resistentes, elevando a qualidade classificatória do algodão colhido (HVI).</li><li>Redução da incidência de apodrecimento de maçãs por deficiência de cálcio.</li><li>Maior tolerância ao estresse hídrico durante o período crítico de enchimento de capulhos.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1615473967657-9dc21773daa3?auto=format&fit=crop&w=800&q=80",
            "icone": "cloud"
        },
        {
            "slug": "silvicultura",
            "nome": "Silvicultura / Eucalipto",
            "resumo": "Potencializa o crescimento volumétrico de espécies florestais (eucalipto, pinus) ao corrigir a acidez subsuperficial e fornecer cálcio para a lignificação acelerada do tronco.",
            "aplicacao": "<ul><li><strong>Cova de Plantio:</strong> 150g a 250g por cova misturados ao substrato de enchimento para mudas clonais de eucalipto.</li><li><strong>Manutenção:</strong> 300 kg a 500 kg/ha aplicados a lanço entre o 1º e o 2º ano de crescimento, na projeção da copa.</li></ul>",
            "resultados": "<ul><li>Incremento significativo no volume de madeira por hectare (IMA) nas rotações de curto prazo (6–7 anos).</li><li>Sistema radicular mais profundo, conferindo maior resistência ao tombamento por ventos fortes.</li><li>Melhoria na qualidade da madeira para celulose devido ao aporte equilibrado de minerais na lignina.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?auto=format&fit=crop&w=800&q=80",
            "icone": "tree-pine"
        },
        {
            "slug": "arroz",
            "nome": "Arroz",
            "resumo": "Atua na correção de solos alagados (várzeas) e de terras altas, melhorando a disponibilidade de fósforo e silício para o fortalecimento dos colmos e aumento do peso de grãos.",
            "aplicacao": "<ul><li><strong>Arroz Irrigado (Várzea):</strong> 300 kg a 500 kg/ha incorporados antes da inundação para neutralizar a toxicidade de ferro ferroso (Fe²⁺) comum em solos alagados.</li><li><strong>Arroz de Terras Altas:</strong> 200 kg a 400 kg/ha no sulco de plantio para garantir arranque vigoroso em solos ácidos de cerrado.</li></ul>",
            "resultados": "<ul><li>Redução drástica do bronzeamento foliar causado por toxidez de ferro em lavouras irrigadas.</li><li>Colmos mais rígidos e resistentes ao acamamento, evitando perdas na colheita mecanizada.</li><li>Grãos mais pesados e com menor índice de gessamento, elevando a classificação comercial.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1536304993881-460e32be1755?auto=format&fit=crop&w=800&q=80",
            "icone": "droplets"
        },
        {
            "slug": "trigo",
            "nome": "Trigo",
            "resumo": "Fortalece a estrutura dos colmos e melhora o enchimento de grãos do trigo, fornecendo cálcio e silício biogênicos que aumentam a tolerância a doenças fúngicas foliares.",
            "aplicacao": "<ul><li><strong>Pré-Plantio:</strong> 200 kg a 400 kg/ha incorporados na camada superficial do solo (0–10 cm) antes da semeadura.</li><li><strong>Perfilhamento:</strong> Aplicação foliar micronizada (0,5% na calda) durante o perfilhamento para fortalecer a epiderme foliar contra ferrugem e oídio.</li></ul>",
            "resultados": "<ul><li>Redução na severidade de manchas foliares e ferrugem-da-folha pela deposição de silício na cutícula.</li><li>Maior peso hectolítrico (PH) dos grãos, essencial para a classificação e comercialização.</li><li>Colmos mais resistentes ao acamamento em cultivares de porte alto sob alta adubação nitrogenada.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1437252611977-07f74518abd7?auto=format&fit=crop&w=800&q=80",
            "icone": "wheat"
        },
        {
            "slug": "citros",
            "nome": "Citros",
            "resumo": "Essencial para a citricultura, o Lithothamnium fornece cálcio de rápida absorção que previne a queda de frutos jovens e melhora a casca e o teor de suco nas laranjas, limões e tangerinas.",
            "aplicacao": "<ul><li><strong>Implantação de Pomares:</strong> 200g a 400g por cova na implantação de mudas de porta-enxerto.</li><li><strong>Produção:</strong> 2 kg a 4 kg por planta/ano, aplicados na projeção da copa no início da estação chuvosa.</li><li><strong>Foliar:</strong> Pulverização com formulação micronizada a 0,5% durante o pegamento de frutos (chumbinho) para reduzir abortamento.</li></ul>",
            "resultados": "<ul><li>Maior fixação de frutos (menor taxa de abortamento pós-florada), aumentando a produtividade por planta.</li><li>Casca mais firme e uniforme, reduzindo perdas na pós-colheita e no transporte.</li><li>Aumento no ratio (relação sólidos solúveis/acidez), melhorando a qualidade do suco para a indústria.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1611080626919-7cf5a9dbab5b?auto=format&fit=crop&w=800&q=80",
            "icone": "citrus"
        },
        {
            "slug": "pecuaria",
            "nome": "Pecuária",
            "resumo": "Na pecuária, o Lithothamnium atua como um excelente suplemento mineral tamponante para o rúmen de bovinos, prevenindo a acidose metabólica e otimizando a conversão alimentar.",
            "aplicacao": "<ul><li><strong>Nutrição Animal:</strong> Adição de 50g a 100g por cabeça/dia na ração de vacas leiteiras ou bovinos de corte.</li><li><strong>Mistura Mineral:</strong> Inclusão de 10% a 15% no sal mineralizado para fornecimento de cálcio e magnésio altamente biodisponíveis.</li></ul>",
            "resultados": "<ul><li>Prevenção da acidose ruminal subclínica em dietas de alta energia.</li><li>Aumento na digestibilidade das fibras das pastagens.</li><li>Melhoria na conversão alimentar, ganho de peso e estabilização da produção de leite.</li></ul>",
            "imagem": "https://images.unsplash.com/photo-1543590333-5741f2431352?auto=format&fit=crop&w=800&q=80",
            "icone": "cow"
        },
        # ──────────────────────────────────────────────
        # GERAL (catch-all)
        # ──────────────────────────────────────────────
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
            "imagem": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=800&q=80",
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
            "imagem": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=800&q=80",
            "cultura": "geral"
        },
        {
            "titulo": "Como o Lithothamnium Desbloqueia o Fósforo Aprisionado no Solo",
            "resumo": "Mais de 80% do fósforo applied na agricultura tropical é adsorvido pelas argilas do solo. Descubra como a alga calcária liberta esse nutriente para as plantas.",
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
            "imagem": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=800&q=80",
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
            "imagem": "https://images.unsplash.com/photo-1592417817098-8f3d6eb19675?auto=format&fit=crop&w=800&q=80",
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
            "imagem": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80",
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
