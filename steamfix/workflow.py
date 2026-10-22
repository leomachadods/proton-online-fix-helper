"""Fluxo simples para jogar; ferramentas técnicas ficam no submenu avançado."""
from pathlib import Path

from . import packages
from .ui import ask, choose, location, message, status, run_command

BACKEND = Path(__file__).resolve().parents[1]/'steam-dll-fix.sh'

MAIN_ACTIONS = [
    ('Preparar e jogar\nConfigura o necessário com os arquivos disponíveis e abre o jogo.', 'play'),
    ('Aplicar correção sem abrir o jogo\nConfigura as DLLs no prefixo. Usa Proton, mas não inicia o jogo.', 'prepare'),
    ('Opções avançadas\nDiagnóstico, instalação manual de arquivos e reversão.', 'advanced'),
    ('Sair', 'exit'),
]

ADVANCED_ACTIONS = [
    ('Ver detalhes da configuração\nMostra as DLLs e consulta o registro usando Proton.', 'check'),
    ('Instalar arquivos de um pacote local\nVocê informa uma pasta já extraída; os originais são guardados em backup.', 'import'),
    ('Ver alterações propostas\nSó mostra o que seria configurado, sem executar Proton.', 'preview'),
    ('Configurar sem abrir o jogo\nAplica os overrides das DLLs já presentes.', 'apply'),
    ('Desfazer configuração de DLLs\nRemove overrides; não restaura nem apaga arquivos importados.', 'remove'),
    ('Voltar', 'back'),
]


def run_backend(command, options):
    return run_command(['bash', str(BACKEND), command, *options])


def import_files(folder):
    message('Use um pacote específico para este jogo, de uma origem em que você confia.\n'
            'Não baixamos arquivos automaticamente. Extraia o pacote antes de continuar.', 'Instalar pacote local')
    value = ask('Pasta do pacote (Enter para voltar): ')
    if not value:
        return False
    source = location(value)
    try:
        files = packages.plan(source, folder)
    except ValueError as exc:
        message(f'Não foi possível importar: {exc}', 'Importação cancelada')
        return False
    message('Arquivos que serão copiados:\n' + '\n'.join(str(p.relative_to(source)) for p in files) +
            '\n\nEsses arquivos podem executar código no seu computador.\n'
            'Arquivos substituídos serão guardados em backup.', 'Revisar pacote')
    if ask('Digite COPIAR para instalar, ou Enter para voltar: ') != 'COPIAR':
        return False
    backup = packages.import_package(source, folder)
    message(f'Arquivos instalados. Backup: {backup}', 'Pacote instalado')
    return True


def has_loader(folder):
    # Indício, não verificação de autenticidade/completude do pacote.
    names = {p.name.casefold() for p in folder.iterdir() if p.is_file()}
    return bool(names & {'winmm.dll', 'version.dll', 'winhttp.dll', 'dinput8.dll', 'dxgi.dll'})


def play(folder, options, start_game=True):
    if not has_loader(folder):
        action = choose([
            ('Já tenho um pacote — escolher pasta', 'import'),
            ('Abrir com os arquivos atuais' if start_game else 'Continuar com os arquivos atuais', 'continue'),
            ('Voltar', 'back')], 'Antes de jogar' if start_game else 'Antes de configurar',
            'Não encontrei um dos carregadores de DLL mais comuns na pasta do jogo. '
            'Isso não prova que o pacote esteja ausente: alguns jogos usam outros arquivos.')
        if action == 'back':
            return
        if action == 'import' and not import_files(folder):
            return
    status('Preparando o jogo…')
    code = run_backend('launch' if start_game else 'apply', options)
    if code:
        message('Não foi possível concluir a preparação ou execução. '
              'Veja a mensagem acima. Use Opções avançadas → Ver detalhes da configuração '
               'se precisar investigar.', 'O jogo não pôde ser iniciado' if start_game else 'A configuração não foi concluída')
    else:
        status('A execução terminou. Você pode jogar novamente ou sair.' if start_game else
               'Configuração concluída. O jogo não foi aberto; você pode iniciá-lo depois pela Steam.')


def advanced(folder, prefix, proton, options):
    while True:
        action = choose(ADVANCED_ACTIONS, 'Opções avançadas',
                        f'Jogo: {folder.name}\nPrefixo: {prefix}\nProton: {proton.name}\n'
                        'Feche o jogo antes de modificar arquivos ou configurações.')
        if action == 'back':
            return
        if action == 'import':
            import_files(folder)
            continue
        if action in ('apply', 'remove', 'check'):
            message('Esta ação executa Proton. As DLLs presentes devem ser confiáveis.', 'Confirmação')
            if ask('Continuar? [s/N]: ').lower() != 's':
                continue
        command = 'apply' if action == 'preview' else action
        extra = ['--dry-run'] if action == 'preview' else []
        code = run_backend(command, options + extra)
        status('Concluído.' if code == 0 else 'A operação falhou. Consulte o log mostrado no resultado.')


def actions_menu(folder, prefix, proton, options):
    while True:
        action = choose(MAIN_ACTIONS, folder.name,
                        'Escolha se deseja jogar agora ou apenas configurar para jogar depois.\n'
                        'Use apenas arquivos confiáveis e feche outras instâncias antes de continuar. '
                        'Este assistente não baixa pacotes nem garante a conexão multiplayer.')
        if action == 'exit':
            return
        if action == 'advanced':
            advanced(folder, prefix, proton, options)
        else:
            play(folder, options, start_game=action == 'play')
