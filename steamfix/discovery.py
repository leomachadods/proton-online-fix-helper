"""Descoberta somente leitura; não executa Steam nem Proton."""
import os
from pathlib import Path
import re


def find_root():
    override = os.environ.get('STEAM_ROOT')
    paths = [override] if override else [
        '~/.local/share/Steam', '~/.steam/steam', '~/.steam/root',
        '~/.var/app/com.valvesoftware.Steam/.local/share/Steam']
    return next((Path(p).expanduser().resolve() for p in paths
                 if (Path(p).expanduser()/'steamapps').is_dir()), None)


def libraries(root):
    result = {root.resolve()}
    vdf = root/'steamapps/libraryfolders.vdf'
    if vdf.is_file():
        for value in re.findall(r'"path"\s+"([^"\n]+)"', vdf.read_text(errors='replace')):
            p = Path(value.replace('\\\\', '\\')).expanduser().resolve()
            if (p/'steamapps').is_dir():
                result.add(p)
    return result


def games(libs):
    result = []
    for library in sorted(libs):
        common = (library/'steamapps/common').resolve()
        for manifest in sorted((library/'steamapps').glob('appmanifest_*.acf')):
            fields = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', manifest.read_text(errors='replace')))
            appid, dirname = fields.get('appid', ''), fields.get('installdir', '')
            # Ferramentas de compatibilidade também têm manifestos e .exe.
            # Não oferecê-las como se fossem jogos configuráveis.
            title = fields.get('name', dirname)
            if title.casefold().startswith(('proton', 'steam linux runtime',
                                           'steamworks common redistributables')):
                continue
            folder = (common/dirname).resolve()
            if not dirname or not folder.is_relative_to(common):
                continue
            if appid.isdecimal() and folder.is_dir() and any(
                    p.suffix.lower() == '.exe' for p in folder.rglob('*') if p.is_file()):
                result.append((f"{title}\nAppID: {appid}\nPasta: {folder}", (folder, appid, library)))
    return sorted(result, key=lambda item: item[0].casefold())


def prefix_proton(prefix):
    config = prefix/'config_info'
    if config.is_file():
        for line in config.read_text(errors='replace').splitlines():
            if '/files/share/fonts/' in line:
                return Path(line.split('/files/share/fonts/', 1)[0])
    return None


def prefixes(libs, appid, game_library=None):
    result = []
    seen = set()
    names = {}
    for lib in sorted(libs):
        for manifest in (lib/'steamapps').glob('appmanifest_*.acf'):
            fields = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', manifest.read_text(errors='replace')))
            if fields.get('appid') and fields.get('name'):
                names[fields['appid']] = fields['name']
    for lib in sorted(libs):
        for p in sorted((lib/'steamapps/compatdata').glob('*')):
            if p.name.isdecimal() and p.resolve() not in seen and (p/'pfx/user.reg').is_file():
                seen.add(p.resolve())
                match = bool(appid) and p.name == appid
                same_library = game_library is not None and lib.resolve() == game_library.resolve()
                recommended = match and same_library
                hint = 'RECOMENDADO — prefixo deste jogo' if recommended else (
                    'AppID correspondente — confira a biblioteca' if match else 'Outro prefixo')
                proton = prefix_proton(p)
                label = (f'{hint}\n'
                         f'Jogo: {names.get(p.name, "Sem nome identificado (pode ser atalho não-Steam)")}\n'
                         f'ID do prefixo: {p.name}\n'
                         f'Proton registrado: {proton.name if proton else "Não identificado"}\n'
                         f'Caminho: {p / "pfx"}')
                result.append((label, p))
    return sorted(result, key=lambda item: (
        not (item[1].name == appid and game_library is not None and
             item[1].parent.parent.parent.resolve() == game_library.resolve()),
        item[1].name != appid, item[1].name, str(item[1])))


def protons(root, libs):
    paths = set((root/'compatibilitytools.d').glob('*/proton'))
    for lib in libs:
        paths.update((lib/'steamapps/common').glob('*/proton'))
    return [(str(p.parent), p.parent) for p in sorted(paths) if p.is_file() and os.access(p, os.X_OK)]
