"""Orquestra o menu; chamadas ao backend usam argv, nunca shell=True."""
import os
from pathlib import Path

from . import discovery
from .ui import ask, choose, location, GoBack, message
from .workflow import actions_menu

BACKEND = Path(__file__).resolve().parents[1]/'steam-dll-fix.sh'


def select_game(libs):
    items = discovery.games(libs) + [('Informar caminho de outro jogo/executável', None)]
    game = choose(items, '1/3 — Escolha seu jogo',
                  'Selecione o jogo que deseja configurar. Nenhuma alteração será feita nesta etapa.')
    if game is None:
        answer = ask('Pasta do jogo ou executável: ')
        if not answer:
            raise GoBack()
        folder = location(answer)
        if folder.is_file():
            folder = folder.parent
        if not folder.is_dir():
            raise ValueError('Pasta inexistente.')
        return folder, '', None
    return game


def select_prefix(root, libs, folder, appid, game_library):
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
    return prefix


def select_proton(root, libs, prefix):
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
        answer = ask('Pasta que contém o arquivo proton: ')
        if not answer:
            raise GoBack()
        proton = location(answer)
    if not (proton/'proton').is_file() or not os.access(proton/'proton', os.X_OK):
        raise ValueError('Proton inválido ou sem permissão de execução.')
    return proton


def main():
    if not BACKEND.is_file():
        raise ValueError(f'Backend ausente: {BACKEND}')
    root = discovery.find_root()
    if root is None:
        answer = ask('Pasta de instalação do Steam: ')
        if not answer:
            return
        root = location(answer)
    if not (root/'steamapps').is_dir():
        raise ValueError('Instalação Steam inválida.')
    libs = discovery.libraries(root)
    stage = 0
    while stage < 3:
        try:
            if stage == 0:
                folder, appid, game_library = select_game(libs)
            elif stage == 1:
                prefix = select_prefix(root, libs, folder, appid, game_library)
            else:
                proton = select_proton(root, libs, prefix)
        except GoBack:
            if stage == 0:
                return
            stage -= 1
            continue
        except (OSError, ValueError) as exc:
            message(str(exc), 'Confira sua seleção')
            stage = max(0, stage - 1)
            continue
        stage += 1
    options = ['--path', str(folder), '--compatdata', prefix.name,
               '--steam-root', str(root), '--proton', str(proton), '--no-config', '--no-netsock']
    actions_menu(folder, prefix, proton, options)
