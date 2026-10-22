"""Orquestra o menu; chamadas ao backend usam argv, nunca shell=True."""
import os
from pathlib import Path

from . import discovery
from .ui import ask, choose, location
from .workflow import actions_menu

BACKEND = Path(__file__).resolve().parents[1]/'steam-dll-fix.sh'


def main():
    if not BACKEND.is_file():
        raise ValueError(f'Backend ausente: {BACKEND}')
    root = discovery.find_root()
    if root is None:
        root = location(ask('Pasta de instalação do Steam: '))
    if not (root/'steamapps').is_dir():
        raise ValueError('Instalação Steam inválida.')
    libs = discovery.libraries(root)
    items = discovery.games(libs) + [('Informar caminho de outro jogo/executável', None)]
    game = choose(items, 'PROTON ONLINE FIX HELPER  •  1/3 — Jogo',
                  'Selecione o jogo que deseja configurar. Nenhuma alteração será feita nesta etapa.')
    if game is None:
        folder = location(ask('Pasta do jogo ou executável: '))
        if folder.is_file():
            folder = folder.parent
        if not folder.is_dir():
            raise ValueError('Pasta inexistente.')
        appid = ''
        game_library = None
    else:
        folder, appid, game_library = game
    prefix = choose(discovery.prefixes(libs, appid, game_library),
                    '2/3 — Ambiente Windows (prefixo Proton)',
                    f'Jogo selecionado: {folder.name}\n'
                    'O prefixo guarda o registro Windows, configurações e possíveis saves do jogo. '
                    'Os overrides serão aplicados somente ao prefixo escolhido.\n'
                    'Se houver uma correspondência de AppID e biblioteca, ela aparece primeiro como '
                    'RECOMENDADO. Não escolha um prefixo de outro jogo por tentativa. '
                    'Se não encontrar o correto, cancele e abra o jogo uma vez pela Steam.')
    # Não permitir que o backend use silenciosamente o prefixo homônimo da raiz.
    if prefix.parent.parent.parent.resolve() != root:
        raise ValueError('Prefixos em biblioteca externa ainda não são suportados pelo backend. Nenhuma alteração feita.')
    recorded = discovery.prefix_proton(prefix)
    proton_items = discovery.protons(root, libs)
    proton_items.sort(key=lambda item: recorded is None or item[1].resolve() != recorded.resolve())
    proton_items = [((f'RECOMENDADO — {p.name}\nRegistrado neste prefixo\nCaminho: {p}'
                      if recorded is not None and p.resolve() == recorded.resolve()
                      else f'{p.name}\nCaminho: {p}'), p) for _, p in proton_items]
    proton = choose(proton_items + [('Informar outro Proton', None)],
                    '3/3 — Versão do Proton',
                    f'Prefixo selecionado: {prefix.name}\n'
                    'Prefira a versão registrada neste prefixo. Trocar versões pode atualizar seu ambiente Windows.')
    if proton is None:
        proton = location(ask('Pasta que contém o arquivo proton: '))
    if not (proton/'proton').is_file() or not os.access(proton/'proton', os.X_OK):
        raise ValueError('Proton inválido ou sem permissão de execução.')
    options = ['--path', str(folder), '--compatdata', prefix.name,
               '--steam-root', str(root), '--proton', str(proton), '--no-config', '--no-netsock']
    actions_menu(folder, prefix, proton, options)
