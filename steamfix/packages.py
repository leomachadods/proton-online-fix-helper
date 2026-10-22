"""Importação local com validação e rollback. Nunca baixa nem executa pacotes."""
import datetime
from pathlib import Path
import shutil
import stat


def plan(source, folder):
    source, folder = Path(source).resolve(), Path(folder).resolve()
    if not source.is_dir() or not folder.is_dir() or source == folder or source in folder.parents or folder in source.parents:
        raise ValueError('Use uma pasta de pacote separada do jogo.')
    files = []
    for p in sorted(source.rglob('*')):
        mode = p.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError('Pacote com links ou arquivos especiais recusado.')
        rel = p.relative_to(source)
        dest = folder/rel
        # Não seguir links nem mesmo se apontam para dentro da pasta do jogo.
        for part in [dest, *dest.parents]:
            if part == folder:
                break
            if part.is_symlink():
                raise ValueError('Destino com link simbólico recusado.')
        if not dest.resolve().is_relative_to(folder):
            raise ValueError('Destino fora da pasta do jogo.')
        if p.is_file():
            if dest.exists() and not dest.is_file():
                raise ValueError('Conflito de diretório no destino.')
            if any(x.exists() and not x.is_dir() for x in dest.parents if x != folder):
                raise ValueError('Diretório pai do destino é um arquivo.')
            files.append(p)
    if not files:
        raise ValueError('Pacote vazio.')
    return files


def import_package(source, folder):
    source, folder = Path(source).resolve(), Path(folder).resolve()
    files = plan(source, folder)
    backup = folder/('.steam-fix-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir()
    copied, created = [], []
    try:
        for p in files:
            dest = folder/p.relative_to(source)
            saved = backup/p.relative_to(source)
            existed = dest.exists()
            if existed:
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, saved)
            missing = []
            parent = dest.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for parent in reversed(missing):
                parent.mkdir()
                created.append(parent)
            copied.append((dest, saved, existed))
            shutil.copy2(p, dest)
        (backup/'arquivos-copiados.txt').write_text('\n'.join(str(p.relative_to(source)) for p in files))
    except BaseException:
        for dest, saved, existed in reversed(copied):
            if existed:
                shutil.copy2(saved, dest)
            else:
                dest.unlink(missing_ok=True)
        for parent in reversed(created):
            parent.rmdir()
        raise
    return backup
