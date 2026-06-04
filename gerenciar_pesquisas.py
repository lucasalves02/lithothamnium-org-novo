"""
gerenciar_pesquisas.py - Gerenciamento de artigos no banco de dados

Lista todos os artigos cadastrados e permite remover os irrelevantes,
mantendo um histórico (blacklist) para que não sejam re-adicionados.

Uso:
    python gerenciar_pesquisas.py              # Lista todos os artigos
    python gerenciar_pesquisas.py --removidos  # Lista artigos na blacklist
"""

import sqlite3
import os
from datetime import datetime


def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(diretorio_atual, 'pesquisas.db')

    if not os.path.exists(caminho_banco):
        print("[Erro] Banco de dados pesquisas.db não encontrado.")
        print("Execute primeiro: python ingest_pdfs.py")
        exit(1)

    conn = sqlite3.connect(caminho_banco)
    conn.row_factory = sqlite3.Row

    # Garante que a tabela de blacklist exista
    conn.execute('''
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


def listar_pesquisas(conn):
    """Lista todas as pesquisas cadastradas no banco."""
    cursor = conn.cursor()
    cursor.execute('SELECT id, titulo, cultura, data_coleta FROM pesquisas ORDER BY id ASC')
    pesquisas = cursor.fetchall()

    if not pesquisas:
        print("\nNenhuma pesquisa cadastrada no banco de dados.")
        return []

    print(f"\n{'='*80}")
    print(f"  PESQUISAS CADASTRADAS ({len(pesquisas)} artigos)")
    print(f"{'='*80}\n")

    for p in pesquisas:
        cultura_fmt = p['cultura'].replace('_', '/').capitalize() if p['cultura'] else 'N/A'
        print(f"  [{p['id']:3d}]  {p['titulo'][:65]}")
        print(f"         Cultura: {cultura_fmt}  |  Coletado em: {p['data_coleta'] or 'N/A'}")
        print()

    return pesquisas


def listar_removidos(conn):
    """Lista todos os artigos na blacklist (removidos)."""
    cursor = conn.cursor()
    cursor.execute('SELECT id, titulo, motivo, data_remocao FROM pesquisas_removidas ORDER BY id ASC')
    removidos = cursor.fetchall()

    if not removidos:
        print("\nNenhum artigo na lista de removidos (blacklist).")
        return

    print(f"\n{'='*80}")
    print(f"  ARTIGOS REMOVIDOS / BLACKLIST ({len(removidos)} artigos)")
    print(f"{'='*80}\n")

    for r in removidos:
        print(f"  [{r['id']:3d}]  {r['titulo'][:65]}")
        print(f"         Motivo: {r['motivo'] or 'Não informado'}  |  Removido em: {r['data_remocao']}")
        print()


def remover_pesquisas(conn):
    """Permite ao usuário selecionar artigos para remover."""
    pesquisas = listar_pesquisas(conn)
    if not pesquisas:
        return

    print(f"{'─'*80}")
    print("  REMOVER ARTIGOS IRRELEVANTES")
    print(f"{'─'*80}")
    print()
    print("  Digite os IDs dos artigos que deseja remover, separados por vírgula.")
    print("  Exemplo: 5, 12, 18")
    print("  Digite 'q' para sair sem remover nada.")
    print()

    entrada = input("  IDs para remover: ").strip()

    if entrada.lower() in ('q', 'sair', ''):
        print("\n  Nenhum artigo removido.")
        return

    # Parse dos IDs
    try:
        ids = [int(x.strip()) for x in entrada.split(',') if x.strip()]
    except ValueError:
        print("\n  [Erro] Entrada inválida. Use apenas números separados por vírgula.")
        return

    if not ids:
        print("\n  Nenhum ID válido informado.")
        return

    # Busca os artigos que serão removidos para confirmar
    cursor = conn.cursor()
    placeholders = ','.join(['?' for _ in ids])
    cursor.execute(f'SELECT id, titulo, link_original FROM pesquisas WHERE id IN ({placeholders})', ids)
    artigos_encontrados = cursor.fetchall()

    if not artigos_encontrados:
        print("\n  [Aviso] Nenhum artigo encontrado com os IDs informados.")
        return

    ids_nao_encontrados = set(ids) - {a['id'] for a in artigos_encontrados}
    if ids_nao_encontrados:
        print(f"\n  [Aviso] IDs não encontrados e ignorados: {ids_nao_encontrados}")

    print(f"\n  Os seguintes {len(artigos_encontrados)} artigos serão REMOVIDOS:\n")
    for a in artigos_encontrados:
        print(f"    [{a['id']:3d}]  {a['titulo'][:70]}")

    print()
    print("  (Opcional) Informe o motivo da remoção (ou pressione Enter para pular):")
    motivo = input("  Motivo: ").strip() or "Artigo considerado irrelevante pelo administrador"

    confirmacao = input(f"\n  Confirmar remoção de {len(artigos_encontrados)} artigos? (s/n): ").strip().lower()

    if confirmacao != 's':
        print("\n  Operação cancelada.")
        return

    # Executa a remoção
    data_remocao = datetime.now().strftime("%d/%m/%Y %H:%M")
    removidos = 0

    for artigo in artigos_encontrados:
        try:
            # Insere na tabela de blacklist
            cursor.execute('''
                INSERT OR IGNORE INTO pesquisas_removidas (titulo, link_original, motivo, data_remocao)
                VALUES (?, ?, ?, ?)
            ''', (artigo['titulo'], artigo['link_original'], motivo, data_remocao))

            # Remove da tabela principal
            cursor.execute('DELETE FROM pesquisas WHERE id = ?', (artigo['id'],))
            removidos += 1
            print(f"    [Removido] ID {artigo['id']}: {artigo['titulo'][:50]}...")
        except Exception as e:
            print(f"    [Erro] Falha ao remover ID {artigo['id']}: {e}")

    conn.commit()
    print(f"\n  {removidos} artigos removidos e adicionados à blacklist com sucesso!")
    print(f"  Eles NÃO serão re-adicionados em futuras buscas.")


def restaurar_pesquisa(conn):
    """Permite restaurar um artigo da blacklist (remove da blacklist)."""
    cursor = conn.cursor()
    cursor.execute('SELECT id, titulo, link_original FROM pesquisas_removidas ORDER BY id ASC')
    removidos = cursor.fetchall()

    if not removidos:
        print("\nNenhum artigo na blacklist para restaurar.")
        return

    listar_removidos(conn)

    print(f"{'─'*80}")
    print("  RESTAURAR ARTIGO DA BLACKLIST")
    print(f"{'─'*80}")
    print()
    print("  Digite os IDs dos artigos que deseja restaurar (retirar da blacklist).")
    print("  Eles poderão ser re-adicionados na próxima busca.")
    print("  Digite 'q' para sair.")
    print()

    entrada = input("  IDs para restaurar: ").strip()

    if entrada.lower() in ('q', 'sair', ''):
        return

    try:
        ids = [int(x.strip()) for x in entrada.split(',') if x.strip()]
    except ValueError:
        print("\n  [Erro] Entrada inválida.")
        return

    placeholders = ','.join(['?' for _ in ids])
    cursor.execute(f'DELETE FROM pesquisas_removidas WHERE id IN ({placeholders})', ids)
    conn.commit()
    print(f"\n  {cursor.rowcount} artigos restaurados da blacklist!")


def menu_principal():
    """Menu principal interativo."""
    conn = conectar_banco()

    while True:
        print(f"\n{'='*80}")
        print("  GERENCIADOR DE PESQUISAS - Lithothamnium.org")
        print(f"{'='*80}")
        print()
        print("  [1] Listar pesquisas cadastradas")
        print("  [2] Remover pesquisas irrelevantes")
        print("  [3] Ver artigos na blacklist (removidos)")
        print("  [4] Restaurar artigo da blacklist")
        print("  [0] Sair")
        print()

        opcao = input("  Opção: ").strip()

        if opcao == '1':
            listar_pesquisas(conn)
        elif opcao == '2':
            remover_pesquisas(conn)
        elif opcao == '3':
            listar_removidos(conn)
        elif opcao == '4':
            restaurar_pesquisa(conn)
        elif opcao == '0':
            print("\n  Até mais!")
            break
        else:
            print("\n  Opção inválida. Tente novamente.")

    conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gerenciador de pesquisas do Lithothamnium.org")
    parser.add_argument("--removidos", action="store_true", help="Lista apenas os artigos na blacklist")
    args = parser.parse_args()

    if args.removidos:
        conn = conectar_banco()
        listar_removidos(conn)
        conn.close()
    else:
        menu_principal()
