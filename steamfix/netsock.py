"""Patch de rede opt-in (SLSsteam netsock) nas opções de inicialização da Steam.

O projeto não baixa, não valida e não inclui o patch: apenas lê/edita o campo
LaunchOptions do localconfig.vdf para um AppID, com backup e verificação. A
Steam precisa estar fechada para gravar, porque ela pode sobrescrever o arquivo.
"""
from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tempfile
from typing import Dict, Iterable, List, Optional, Tuple

STEAM64_BASE = 76561197960265728
DEFAULT_PATCH_PATHS = (
    '~/.config/SLSsteam/tools/netsock/netsock.so',
    '~/.local/share/SLSsteam/tools/netsock/netsock.so',
    '~/.var/app/com.valvesoftware.Steam/.config/SLSsteam/tools/netsock/netsock.so',
    '~/.var/app/com.valvesoftware.Steam/.local/share/SLSsteam/tools/netsock/netsock.so',
)
# Um único LD_AUDIT=... dentro das opções. Os valores usuais são simples; o
# parser de shell só é usado para comparar o caminho, não para reescrever.
LD_AUDIT_RE = re.compile(r'(?<!\S)LD_AUDIT=(?:"[^"]*"|\'[^\']*\'|\S+)')


class Token:
    __slots__ = ('kind', 'value', 'start', 'end')

    def __init__(self, kind, value, start, end):
        self.kind, self.value, self.start, self.end = kind, value, start, end


class Entry:
    __slots__ = ('key', 'key_start', 'key_end', 'value', 'value_start',
                 'value_end', 'block')

    def __init__(self, key, key_start, key_end, value, value_start, value_end,
                 block=None):
        self.key = key
        self.key_start, self.key_end = key_start, key_end
        self.value = value
        self.value_start, self.value_end = value_start, value_end
        self.block = block


class Block:
    __slots__ = ('entries', 'start', 'end', 'name')

    def __init__(self, entries, start, end, name=None):
        self.entries = entries
        self.start, self.end, self.name = start, end, name


def _unescape(value):
    escapes = {'n': '\n', 'r': '\r', 't': '\t', '"': '"', '\\': '\\'}
    out, i = [], 0
    while i < len(value):
        if value[i] == '\\' and i + 1 < len(value):
            out.append(escapes.get(value[i + 1], value[i + 1]))
            i += 2
        else:
            out.append(value[i])
            i += 1
    return ''.join(out)


def _tokens(text):
    i, size = 0, len(text)
    while i < size:
        char = text[i]
        if char in ' \t\r\n':
            i += 1
            continue
        if text.startswith('//', i):
            line = text.find('\n', i)
            i = size if line < 0 else line + 1
            continue
        if char in '{}':
            yield Token(char, char, i, i + 1)
            i += 1
            continue
        if char == '"':
            start, i, out = i, i + 1, []
            while i < size:
                char = text[i]
                if char == '\\' and i + 1 < size:
                    out.append('\\' + text[i + 1])
                    i += 2
                elif char == '"':
                    i += 1
                    break
                else:
                    out.append(char)
                    i += 1
            else:
                raise ValueError('texto entre aspas não terminado')
            yield Token('string', _unescape(''.join(out)), start, i)
            continue
        start = i
        while i < size and text[i] not in ' \t\r\n{}"':
            if text.startswith('//', i):
                break
            i += 1
        if i == start:
            raise ValueError('caractere inesperado no arquivo')
        yield Token('bare', text[start:i], start, i)


def parse_vdf(text):
    """Parser pequeno e somente leitura, preservando as posições do original."""
    tokens = list(_tokens(text))

    def block_at(pos, name):
        if pos >= len(tokens) or tokens[pos].kind != '{':
            raise ValueError('bloco esperado')
        block = Block({}, tokens[pos].start, len(text), name)
        pos += 1
        while pos < len(tokens):
            token = tokens[pos]
            if token.kind == '}':
                block.end = token.end
                return block, pos + 1
            if token.kind not in ('string', 'bare'):
                raise ValueError('chave inesperada')
            key, key_start, key_end = token.value, token.start, token.end
            pos += 1
            if pos >= len(tokens):
                raise ValueError('valor ausente')
            value = tokens[pos]
            if value.kind == '{':
                child, pos = block_at(pos, key)
                entry = Entry(key, key_start, key_end, child, child.start,
                              child.end, child)
            elif value.kind in ('string', 'bare'):
                entry = Entry(key, key_start, key_end, value.value,
                              value.start, value.end)
                pos += 1
            else:
                raise ValueError('valor inesperado')
            block.entries[key] = entry
        raise ValueError('bloco não terminado')

    root = Block({}, 0, len(text))
    pos = 0
    while pos < len(tokens):
        token = tokens[pos]
        if token.kind not in ('string', 'bare'):
            raise ValueError('chave de topo inesperada')
        key, key_start, key_end = token.value, token.start, token.end
        pos += 1
        if pos >= len(tokens) or tokens[pos].kind != '{':
            raise ValueError('bloco de topo esperado')
        child, pos = block_at(pos, key)
        root.entries[key] = Entry(key, key_start, key_end, child, child.start,
                                  child.end, child)
    return root


def _walk(block):
    yield block
    for entry in block.entries.values():
        if isinstance(entry.value, Block):
            yield from _walk(entry.value)


def find_app_block(root, appid):
    appid = str(appid)
    # Primeiro procura dentro de um bloco "apps" (estrutura normal do Steam).
    for block in _walk(root):
        if block.name != 'apps':
            continue
        entry = block.entries.get(appid)
        if entry is not None and isinstance(entry.value, Block):
            return entry.value
    # Fallback para variantes de arquivo que não nomeiam o bloco "apps".
    for block in _walk(root):
        entry = block.entries.get(appid)
        if entry is not None and isinstance(entry.value, Block):
            return entry.value
    return None


def read_launch_options(text, appid):
    root = parse_vdf(text)
    app = find_app_block(root, appid)
    if app is None:
        raise ValueError('AppID %s não encontrado nas opções da Steam' % appid)
    entry = app.entries.get('LaunchOptions')
    if entry is not None and not isinstance(entry.value, str):
        raise ValueError('LaunchOptions inválido para o AppID %s' % appid)
    return app, entry


def _read(path):
    with open(path, 'r', encoding='utf-8', errors='replace', newline='') as handle:
        return handle.read()


def active_steam_id(root):
    path = Path(root)/'config/loginusers.vdf'
    if not path.is_file():
        return None
    try:
        tree = parse_vdf(_read(path))
    except (OSError, ValueError):
        return None
    users = tree.entries.get('users')
    if users is None or not isinstance(users.value, Block):
        return None
    auto = []
    for steamid, entry in users.value.entries.items():
        if not re.fullmatch(r'\d{17}', steamid):
            continue
        if not isinstance(entry.value, Block):
            continue
        def field(name):
            item = entry.value.entries.get(name)
            return item.value if item is not None and isinstance(item.value, str) else ''
        if field('MostRecent') == '1':
            return steamid
        if field('AutoLogin') == '1':
            auto.append(steamid)
    return auto[0] if auto else None


def account_config(root, steamid):
    try:
        account = int(steamid) - STEAM64_BASE
    except (TypeError, ValueError):
        return None
    if account <= 0:
        return None
    return Path(root)/'userdata'/str(account)/'config/localconfig.vdf'


def config_paths(root):
    return sorted((Path(root)/'userdata').glob('*/config/localconfig.vdf'))


def select_config(root, appid, userdata=None):
    """Prioriza a conta ativa; aceita uma conta específica ou a única existente."""
    if userdata:
        path = Path(userdata).expanduser()
        if path.is_dir():
            path = path/'config/localconfig.vdf'
        if not path.is_file():
            raise ValueError('localconfig.vdf não encontrado: %s' % path)
        return path
    active = active_steam_id(root)
    if active:
        candidate = account_config(root, active)
        if candidate is not None and candidate.is_file():
            try:
                read_launch_options(_read(candidate), appid)
            except (OSError, ValueError):
                pass
            else:
                return candidate
    candidates = []
    for path in config_paths(root):
        try:
            read_launch_options(_read(path), appid)
        except (OSError, ValueError):
            continue
        candidates.append(path)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError('AppID %s aparece em várias contas Steam; use --userdata' % appid)
    raise ValueError('AppID %s não encontrado nas opções da Steam' % appid)


def find_patch(explicit=None):
    if explicit:
        return Path(explicit).expanduser()
    for raw in DEFAULT_PATCH_PATHS:
        path = Path(raw).expanduser()
        if path.is_file():
            return path
    return None


def require_patch(explicit=None):
    path = find_patch(explicit)
    if path is None or not path.is_file():
        raise ValueError('patch netsock.so não encontrado; informe --patch CAMINHO')
    return path


def _same_path(value, patch):
    if value is None or patch is None:
        return False
    try:
        expanded = os.path.expandvars(os.path.expanduser(str(value)))
        return Path(expanded).resolve() == Path(patch).expanduser().resolve()
    except (OSError, ValueError):
        return False


def _ld_audit_values(value):
    found = []
    for match in LD_AUDIT_RE.findall(value or ''):
        try:
            parts = shlex.split(match)
        except ValueError:
            parts = []
        if len(parts) == 1 and parts[0].startswith('LD_AUDIT='):
            found.append((match, parts[0].split('=', 1)[1]))
        else:
            found.append((match, None))
    return found


def _token(patch):
    return 'LD_AUDIT=' + shlex.quote(str(patch))


def _squash_spaces(value):
    """Remove espaços repetidos fora de aspas, sem mexer no conteúdo citado."""
    out, quote, previous_space = [], None, False
    i = 0
    while i < len(value):
        char = value[i]
        if quote:
            out.append(char)
            if char == '\\' and i + 1 < len(value):
                out.append(value[i + 1])
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
            continue
        if char in ('"', "'"):
            quote = char
            out.append(char)
            previous_space = False
        elif char in ' \t':
            if not previous_space:
                out.append(' ')
            previous_space = True
        else:
            out.append(char)
            previous_space = False
        i += 1
    return ''.join(out).strip()


def compose_launch_options(current, patch, force=False):
    current = (current or '').strip()
    token = _token(patch)
    found = _ld_audit_values(current)
    if found:
        if all(_same_path(value, patch) for _, value in found):
            if len(found) == 1:
                return current
            # Duplicatas do mesmo caminho: deixa somente uma.
            current = _squash_spaces(LD_AUDIT_RE.sub('', current))
        else:
            if not force:
                raise ValueError('já existe um LD_AUDIT diferente; use --force para substituir')
            current = _squash_spaces(LD_AUDIT_RE.sub('', current))
    if '%command%' in current:
        index = current.index('%command%')
        before, after = current[:index].rstrip(), current[index:]
        current = (before + ' ' if before else '') + token + ' ' + after
    else:
        current = (current + ' ' if current else '') + token + ' %command%'
    return _squash_spaces(current)


def strip_launch_options(current, patch, force=False):
    current = (current or '').strip()
    found = _ld_audit_values(current)
    if not found:
        return current
    if not force and any(not _same_path(value, patch) for _, value in found):
        raise ValueError('há um LD_AUDIT diferente do patch informado; use --force')
    return _squash_spaces(LD_AUDIT_RE.sub('', current))


def current_launch_options(root, appid, userdata=None):
    path = select_config(root, appid, userdata)
    _, entry = read_launch_options(_read(path), str(appid))
    return path, (entry.value if entry is not None else '')



def _vdf_quote(value):
    if any(char in value for char in ('\n', '\r', '\0')):
        raise ValueError('valor com quebra de linha não é aceito')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _closing_indent(text, block):
    position = max(0, block.end - 1)
    start = text.rfind('\n', 0, position) + 1
    prefix = text[start:position]
    return prefix if not prefix.strip() else ''


def write_launch_options(path, appid, value, backup=True):
    if path.is_symlink():
        raise ValueError('localconfig.vdf é um link simbólico; recusado por segurança')
    text = _read(path)
    app, entry = read_launch_options(text, appid)
    if entry is not None:
        new_text = text[:entry.value_start] + _vdf_quote(value) + text[entry.value_end:]
    else:
        newline = '\r\n' if '\r\n' in text else '\n'
        indent = _closing_indent(text, app)
        insertion = newline + indent + '\t"LaunchOptions"\t\t' + _vdf_quote(value) + newline + indent
        position = app.end - 1
        new_text = text[:position] + insertion + text[position:]
    _, check = read_launch_options(new_text, appid)
    if check is None or check.value != value:
        raise ValueError('não foi possível verificar a opção gravada')
    backup_path = None
    if backup:
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup_path = path.with_name(path.name + '.bak-' + stamp)
        shutil.copy2(path, backup_path)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(new_text)
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return backup_path


def steam_running(proc_root=Path('/proc')):
    for entry in Path(proc_root).glob('[0-9]*'):
        try:
            name = (entry/'comm').read_text().strip()
        except OSError:
            continue
        if name in ('steam', 'steamwebhelper'):
            return True
    return False


def _game_dir(root, appid):
    manifest = Path(root)/'steamapps'/('appmanifest_%s.acf' % appid)
    if not manifest.is_file():
        return None
    try:
        match = re.search(r'"installdir"\s+"([^"]*)"', _read(manifest))
    except OSError:
        return None
    if not match:
        return None
    name = match.group(1).replace('\\\\', '\\').replace('\\"', '"')
    candidate = Path(root)/'steamapps/common'/name
    return candidate if candidate.is_dir() else None


def _running_processes(root, appid, proc_root=Path('/proc')):
    directory = _game_dir(root, appid)
    needles = []
    if directory is not None:
        needles.append(str(directory))
        needles.append(str(directory).replace('/', '\\'))
        # Nos processos Wine o caminho aparece como S:\steamapps\common\Jogo\...
        relative = Path('steamapps/common')/directory.name
        needles.append(str(relative))
        needles.append(str(relative).replace('/', '\\'))
    if not needles:
        return []
    found = []
    for entry in Path(proc_root).glob('[0-9]*'):
        try:
            command = (entry/'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
        except OSError:
            continue
        if not any(needle and needle.casefold() in command.casefold() for needle in needles):
            continue
        folded = command.casefold()
        if ('steam-dll-fix.sh' in command or 'proton-online-fix-helper' in command or
                'pressure-vessel' in folded or 'steam-launch-wrapper' in folded or
                ('proton' in folded and 'waitforexitandrun' in folded)):
            continue
        value = None
        try:
            for item in (entry/'environ').read_bytes().split(b'\0'):
                if item.startswith(b'LD_AUDIT='):
                    value = item.split(b'=', 1)[1].decode('utf-8', 'replace')
                    break
        except OSError:
            pass
        found.append({'pid': entry.name, 'cmdline': command[:300], 'ld_audit': value})
    return found


def _safe_line(line, limit=300):
    clean = ''.join(char for char in line if char in '\t' or ord(char) >= 32).strip()
    return clean[:limit]


def _audit_log(root, appid):
    directory = _game_dir(root, appid)
    if directory is None:
        return None
    path = directory/'audit_patch.log'
    if not path.is_file():
        return None
    try:
        lines = [_safe_line(line) for line in _read(path).splitlines() if line.strip()]
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return {'path': path, 'mtime': mtime, 'lines': lines[-10:]}


def _player_log(root, appid):
    prefix = Path(root)/'steamapps/compatdata'/str(appid)/'pfx'
    files = []
    for pattern in ('drive_c/users/*/AppData/LocalLow/*/*/Player.log',
                    'drive_c/users/*/AppData/Local/*/*/Player.log',
                    'drive_c/users/*/AppData/LocalLow/*/*/Player-prev.log'):
        files.extend(prefix.glob(pattern))
    if not files:
        return None
    try:
        path = max(files, key=lambda item: item.stat().st_mtime)
        with path.open('rb') as handle:
            size = path.stat().st_size
            handle.seek(max(0, size - 1000000))
            text = handle.read().decode('utf-8', 'replace')
    except OSError:
        return None
    lines = text.splitlines()
    cert = [line for line in lines if 'Cert is not authorized' in line]
    lost = [line for line in lines if 'connection to the lobby has been lost' in line.casefold()]
    status = []
    for line in lines:
        folded = line.casefold()
        if ('steam api has been initialized' in folded or
                'starting client [steamsockets]' in folded or
                'server started listening' in folded or
                ('lobby' in folded and any(key in folded for key in
                 ('created', 'joined', 'oluşturuldu', 'girildi'))) or
                'code join:' in folded):
            status.append(line)
    return {
        'path': path,
        'mtime': path.stat().st_mtime,
        'cert_errors': len(cert),
        'last_cert': _safe_line(cert[-1]) if cert else '',
        'lost': len(lost),
        'status_lines': [_safe_line(line) for line in status[-5:]],
    }


def diagnostics(root, appid, patch=None, userdata=None, proc_root=Path('/proc')):
    root = Path(root).expanduser()
    appid = str(appid)
    patch_path = find_patch(patch)
    active = active_steam_id(root)
    configs = []
    for path in config_paths(root):
        try:
            _, entry = read_launch_options(_read(path), appid)
        except (OSError, ValueError):
            continue
        value = entry.value if entry is not None else ''
        values = _ld_audit_values(value)
        configs.append({
            'path': path,
            'active': bool(active and account_config(root, active) is not None and
                           path == account_config(root, active)),
            'launch_options': value,
            'has_ld_audit': bool(values),
            'uses_patch': bool(patch_path and any(_same_path(item, patch_path) for _, item in values)),
        })
    return {
        'root': root,
        'appid': appid,
        'patch': patch_path,
        'patch_exists': bool(patch_path and patch_path.is_file()),
        'steam_running': steam_running(),
        'active_steam_id': active,
        'configs': configs,
        'processes': _running_processes(root, appid, proc_root),
        'audit_log': _audit_log(root, appid),
        'player_log': _player_log(root, appid),
    }


def format_diagnostics(info):
    lines = []
    patch = info['patch']
    lines.append('Patch: %s' % (patch if patch else 'não encontrado (informe --patch)'))
    if patch is not None:
        lines.append('  arquivo: %s' % ('ok' if info['patch_exists'] else 'ausente'))
    lines.append('Steam: %s' % ('em execução — feche para aplicar' if info['steam_running'] else 'fechada'))
    if info['active_steam_id']:
        lines.append('Conta ativa: %s' % info['active_steam_id'])
    if not info['configs']:
        lines.append('AppID %s: não encontrado nas opções da Steam.' % info['appid'])
    for config in info['configs']:
        marker = ' (conta ativa)' if config['active'] else ''
        lines.append('Config: %s%s' % (config['path'], marker))
        lines.append('  Opções: %s' % (config['launch_options'] or '(vazias)'))
        if config['uses_patch']:
            state = 'configurado'
        elif config['has_ld_audit']:
            state = 'outro LD_AUDIT'
        else:
            state = 'ausente'
        lines.append('  LD_AUDIT: %s' % state)
    if info['processes']:
        for process in info['processes']:
            lines.append('Jogo em execução: PID %s; LD_AUDIT: %s' % (
                process['pid'], process['ld_audit'] or 'não carregado'))
    else:
        lines.append('Jogo em execução: não detectado')
    audit = info['audit_log']
    if audit:
        lines.append('audit_patch.log: %s' % audit['path'])
        lines.extend('  ' + line for line in audit['lines'][-3:])
    else:
        lines.append('audit_patch.log: não encontrado')
    player = info['player_log']
    if player:
        lines.append('Player.log: %s' % player['path'])
        if player['cert_errors']:
            lines.append('  Erros de certificado: %s' % player['cert_errors'])
            lines.append('  Último: %s' % player['last_cert'])
        else:
            lines.append('  Nenhum erro de certificado encontrado.')
        if player['lost']:
            lines.append('  Quedas de lobby: %s' % player['lost'])
        for line in player['status_lines'][-2:]:
            lines.append('  ' + line)
    else:
        lines.append('Player.log: não encontrado')
    return '\n'.join(lines)


def apply(root, appid, patch=None, userdata=None, force=False, dry_run=False):
    patch_path = require_patch(patch)
    if not dry_run and not force and steam_running():
        raise ValueError('feche a Steam completamente antes de alterar as opções; '
                         'a Steam pode sobrescrever o arquivo ao sair')
    path = select_config(root, appid, userdata)
    text = _read(path)
    _, entry = read_launch_options(text, appid)
    old = entry.value if entry is not None else ''
    new = compose_launch_options(old, patch_path, force=force)
    result = {'path': path, 'old': old, 'new': new, 'backup': None, 'changed': False}
    if new == old:
        return result
    if dry_run:
        result['dry_run'] = True
        return result
    result['backup'] = write_launch_options(path, appid, new, backup=True)
    result['changed'] = True
    return result


def remove(root, appid, patch=None, userdata=None, force=False, dry_run=False):
    patch_path = require_patch(patch)
    if not dry_run and not force and steam_running():
        raise ValueError('feche a Steam completamente antes de alterar as opções; '
                         'a Steam pode sobrescrever o arquivo ao sair')
    path = select_config(root, appid, userdata)
    text = _read(path)
    _, entry = read_launch_options(text, appid)
    old = entry.value if entry is not None else ''
    new = strip_launch_options(old, patch_path, force=force)
    result = {'path': path, 'old': old, 'new': new, 'backup': None, 'changed': False}
    if new == old:
        return result
    if dry_run:
        result['dry_run'] = True
        return result
    result['backup'] = write_launch_options(path, appid, new, backup=True)
    result['changed'] = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Configura o LD_AUDIT do patch SLSsteam nas opções da Steam.')
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('status', 'apply', 'remove'):
        item = sub.add_parser(action)
        item.add_argument('--steam-root', required=True)
        item.add_argument('--appid', required=True)
        item.add_argument('--patch')
        item.add_argument('--userdata')
        item.add_argument('--dry-run', action='store_true')
        item.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'\d+', str(args.appid)):
        print('Erro: AppID inválido', file=sys.stderr)
        return 1
    try:
        if args.action == 'status':
            print(format_diagnostics(diagnostics(args.steam_root, args.appid, args.patch, args.userdata)))
            return 0
        function = apply if args.action == 'apply' else remove
        result = function(args.steam_root, args.appid, args.patch, args.userdata,
                          args.force, args.dry_run)
        print('Config: %s' % result['path'])
        print('Antes: %s' % (result['old'] or '(vazio)'))
        print('Depois: %s' % (result['new'] or '(vazio)'))
        if result.get('dry_run'):
            print('Pré-visualização: nada foi gravado.')
        elif not result['changed']:
            print('Nada a alterar.')
        else:
            print('Opção gravada. Backup: %s' % result['backup'])
            print('Abra a Steam de novo e inicie o jogo para carregar o patch.')
        return 0
    except (OSError, ValueError) as exc:
        print('Erro: %s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
