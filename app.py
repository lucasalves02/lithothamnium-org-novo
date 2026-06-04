from flask import Flask, render_template, request, abort, Response, redirect
import sqlite3
import os
import shutil
import tempfile
import re
import unicodedata

app = Flask(__name__)

@app.template_filter('slugify')
def slugify_filter(value):
    if not value:
        return ""
    # Normalize unicode to decompose accents, e.g. é -> e
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    # Keep only alphanumeric characters, spaces and hyphens
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    # Replace spaces and multiple hyphens with a single hyphen
    return re.sub(r'[-\s]+', '-', value)

# Função para conectar no banco de pesquisas (com suporte a escrita em ambiente Vercel)
def conectar_banco():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco_original = os.path.join(diretorio_atual, 'pesquisas.db')
    caminho_banco_temp = os.path.join(tempfile.gettempdir(), 'pesquisas.db')
    
    if not os.path.exists(caminho_banco_original):
        raise FileNotFoundError("ERRO FATAL: O arquivo pesquisas.db não foi encontrado!")
        
    # Copia para pasta temporária caso não exista ou esteja desatualizado
    if not os.path.exists(caminho_banco_temp) or os.path.getmtime(caminho_banco_original) > os.path.getmtime(caminho_banco_temp):
        shutil.copy2(caminho_banco_original, caminho_banco_temp)
        
    conn = sqlite3.connect(caminho_banco_temp)
    conn.row_factory = sqlite3.Row 
    return conn

# Rota Principal (Homepage Hub)
@app.route('/')
def index():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # 1. Buscar todas as culturas para o explorer (ordem específica de apresentação)
    cursor.execute('SELECT * FROM culturas WHERE slug != "geral" ORDER BY nome ASC')
    culturas = cursor.fetchall()
    
    # 2. Buscar as 3 pesquisas mais recentes
    cursor.execute('SELECT id, titulo, resumo, autores, imagem, cultura FROM pesquisas ORDER BY id DESC LIMIT 3')
    pesquisas = cursor.fetchall()
    
    # 3. Buscar as 3 postagens do blog mais recentes
    cursor.execute('SELECT id, titulo, resumo, autor, data_publicacao, imagem, cultura FROM blog_posts ORDER BY id DESC LIMIT 3')
    blog_posts = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', culturas=culturas, pesquisas=pesquisas, blog_posts=blog_posts)

# Rota de Guia Técnico por Cultura (Café, Pastagens, etc.)
@app.route('/cultura/<slug>')
def cultura(slug):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # 1. Detalhes da cultura
    cursor.execute('SELECT * FROM culturas WHERE slug = ?', (slug,))
    cultura_info = cursor.fetchone()
    
    if cultura_info is None:
        conn.close()
        abort(404)
        
    # 2. Artigos científicos relacionados
    cursor.execute('SELECT id, titulo, resumo, autores, imagem FROM pesquisas WHERE cultura = ? ORDER BY id DESC', (slug,))
    pesquisas = cursor.fetchall()
    
    # 3. Posts de blog relacionados
    cursor.execute('SELECT id, titulo, resumo, data_publicacao, imagem FROM blog_posts WHERE cultura = ? ORDER BY id DESC', (slug,))
    blog_posts = cursor.fetchall()
    
    # 4. Lista de todas as outras culturas para navegação rápida lateral
    cursor.execute('SELECT slug, nome FROM culturas WHERE slug != ? AND slug != "geral" ORDER BY nome ASC', (slug,))
    outras_culturas = cursor.fetchall()
    
    conn.close()
    return render_template('cultura.html', cultura=cultura_info, pesquisas=pesquisas, blog_posts=blog_posts, outras_culturas=outras_culturas)

# Rota da Biblioteca / Pesquisas Científicas (Search & Filter)
@app.route('/artigos')
def artigos():
    busca = request.args.get('q', '').strip()
    cultura_filtro = request.args.get('cultura', '').strip()
    
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Busca todas as culturas para o filtro select
    cursor.execute('SELECT slug, nome FROM culturas ORDER BY nome ASC')
    culturas = cursor.fetchall()
    
    query = 'SELECT id, titulo, resumo, autores, imagem, cultura FROM pesquisas WHERE 1=1'
    params = []
    
    if busca:
        query += ' AND (titulo LIKE ? OR resumo LIKE ? OR conteudo LIKE ?)'
        busca_param = f'%{busca}%'
        params.extend([busca_param, busca_param, busca_param])
        
    if cultura_filtro:
        query += ' AND cultura = ?'
        params.append(cultura_filtro)
        
    query += ' ORDER BY id DESC'
    
    cursor.execute(query, params)
    pesquisas = cursor.fetchall()
    conn.close()
    
    return render_template('artigos.html', pesquisas=pesquisas, culturas=culturas, busca=busca, cultura_filtro=cultura_filtro)

# Rota Dinâmica para Artigo Científico Único
@app.route('/artigo/<slug_or_id>')
def artigo(slug_or_id):
    parts = slug_or_id.split('-', 1)
    try:
        artigo_id = int(parts[0])
    except ValueError:
        abort(404)
        
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pesquisas WHERE id = ?', (artigo_id,))
    pesquisa = cursor.fetchone()
    
    if pesquisa is None:
        conn.close()
        abort(404)
        
    correct_slug = slugify_filter(pesquisa['titulo'])
    expected_path = f"{artigo_id}-{correct_slug}"
    
    if slug_or_id != expected_path:
        conn.close()
        return redirect(f"/artigo/{expected_path}", code=301)
        
    # Buscar artigos relacionados da mesma cultura (excluindo o atual)
    cursor.execute('SELECT id, titulo, imagem, cultura FROM pesquisas WHERE cultura = ? AND id != ? LIMIT 3', (pesquisa['cultura'], artigo_id))
    relacionados = cursor.fetchall()
    
    conn.close()
    return render_template('artigo.html', pesquisa=pesquisa, relacionados=relacionados)

# Rota do Blog Técnico Geral (Search & Filter)
@app.route('/blog')
def blog():
    busca = request.args.get('q', '').strip()
    cultura_filtro = request.args.get('cultura', '').strip()
    
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Busca todas as culturas para o filtro select
    cursor.execute('SELECT slug, nome FROM culturas ORDER BY nome ASC')
    culturas = cursor.fetchall()
    
    query = 'SELECT id, titulo, resumo, autor, data_publicacao, imagem, cultura FROM blog_posts WHERE 1=1'
    params = []
    
    if busca:
        query += ' AND (titulo LIKE ? OR resumo LIKE ? OR conteudo LIKE ?)'
        busca_param = f'%{busca}%'
        params.extend([busca_param, busca_param, busca_param])
        
    if cultura_filtro:
        query += ' AND cultura = ?'
        params.append(cultura_filtro)
        
    query += ' ORDER BY id DESC'
    
    cursor.execute(query, params)
    blog_posts = cursor.fetchall()
    conn.close()
    
    return render_template('blog.html', blog_posts=blog_posts, culturas=culturas, busca=busca, cultura_filtro=cultura_filtro)

# Rota Dinâmica para Postagem Única do Blog
@app.route('/blog/<slug_or_id>')
def blog_post(slug_or_id):
    parts = slug_or_id.split('-', 1)
    try:
        post_id = int(parts[0])
    except ValueError:
        abort(404)
        
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    
    if post is None:
        conn.close()
        abort(404)
        
    correct_slug = slugify_filter(post['titulo'])
    expected_path = f"{post_id}-{correct_slug}"
    
    if slug_or_id != expected_path:
        conn.close()
        return redirect(f"/blog/{expected_path}", code=301)
        
    # Buscar posts relacionados
    cursor.execute('SELECT id, titulo, imagem, cultura FROM blog_posts WHERE cultura = ? AND id != ? LIMIT 3', (post['cultura'], post_id))
    relacionados = cursor.fetchall()
    
    conn.close()
    return render_template('blog_post.html', post=post, relacionados=relacionados)

# Rota para Sitemap Dinâmico (SEO)
@app.route('/sitemap.xml')
def sitemap():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    base_url = request.url_root.rstrip('/')
    if '127.0.0.1' in base_url or 'localhost' in base_url:
        base_url = 'https://lithothamnium.org'
        
    urls = [
        {"loc": f"{base_url}/", "priority": "1.0"},
        {"loc": f"{base_url}/artigos", "priority": "0.8"},
        {"loc": f"{base_url}/blog", "priority": "0.8"},
    ]
    
    # Adiciona culturas
    cursor.execute('SELECT slug FROM culturas')
    for row in cursor.fetchall():
        urls.append({"loc": f"{base_url}/cultura/{row['slug']}", "priority": "0.7"})
        
    # Adiciona artigos científicos
    cursor.execute('SELECT id, titulo FROM pesquisas')
    for row in cursor.fetchall():
        slug = slugify_filter(row['titulo'])
        urls.append({"loc": f"{base_url}/artigo/{row['id']}-{slug}", "priority": "0.6"})
        
    # Adiciona posts de blog
    cursor.execute('SELECT id, titulo FROM blog_posts')
    for row in cursor.fetchall():
        slug = slugify_filter(row['titulo'])
        urls.append({"loc": f"{base_url}/blog/{row['id']}-{slug}", "priority": "0.6"})
        
    conn.close()
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml_content += '  <url>\n'
        xml_content += f"    <loc>{url['loc']}</loc>\n"
        xml_content += f"    <priority>{url['priority']}</priority>\n"
        xml_content += '  </url>\n'
    xml_content += '</urlset>'
    
    return Response(xml_content, mimetype='application/xml')

# Rota para robots.txt (SEO)
@app.route('/robots.txt')
def robots():
    base_url = request.url_root.rstrip('/')
    if '127.0.0.1' in base_url or 'localhost' in base_url:
        base_url = 'https://lithothamnium.org'
    content = f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n"
    return Response(content, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)
