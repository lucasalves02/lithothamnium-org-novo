from flask import Flask, render_template, request, abort
import sqlite3
import os
import shutil
import tempfile

app = Flask(__name__)

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
@app.route('/artigo/<int:id>')
def artigo(id):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pesquisas WHERE id = ?', (id,))
    pesquisa = cursor.fetchone()
    
    if pesquisa is None:
        conn.close()
        abort(404)
        
    # Buscar artigos relacionados da mesma cultura (excluindo o atual)
    cursor.execute('SELECT id, titulo, imagem, cultura FROM pesquisas WHERE cultura = ? AND id != ? LIMIT 3', (pesquisa['cultura'], id))
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
@app.route('/blog/<int:id>')
def blog_post(id):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM blog_posts WHERE id = ?', (id,))
    post = cursor.fetchone()
    
    if post is None:
        conn.close()
        abort(404)
        
    # Buscar posts relacionados
    cursor.execute('SELECT id, titulo, imagem, cultura FROM blog_posts WHERE cultura = ? AND id != ? LIMIT 3', (post['cultura'], id))
    relacionados = cursor.fetchall()
    
    conn.close()
    return render_template('blog_post.html', post=post, relacionados=relacionados)

if __name__ == '__main__':
    app.run(debug=True)
