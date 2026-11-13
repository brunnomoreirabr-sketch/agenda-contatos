"""Cria um atalho no Linux ou um aplicativo lançador no macOS."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def install():
    if sys.platform == 'win32':
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-File', str(Path(__file__).with_name('instalar_windows.ps1'))], check=True)
        return
    source = Path(__file__).resolve().parent
    destination = Path.home() / '.local' / 'share' / 'agenda-contatos-app'
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'agenda.py', destination)
    shutil.copytree(source / 'agenda', destination / 'agenda', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    if sys.platform == 'darwin':
        app = Path.home() / 'Desktop' / 'Agenda de Contatos.app' / 'Contents'
        (app / 'MacOS').mkdir(parents=True, exist_ok=True)
        launcher = app / 'MacOS' / 'agenda'
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                            shlex.quote(str(destination / 'agenda.py')) + '\n')
        launcher.chmod(0o755)
        (app / 'Info.plist').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<plist version="1.0"><dict><key>CFBundleExecutable</key><string>agenda</string>'
            '<key>CFBundleName</key><string>Agenda de Contatos</string>'
            '<key>CFBundlePackageType</key><string>APPL</string></dict></plist>')
        print('Aplicativo criado em:', app.parent)
        return
    try:
        desktop = Path(subprocess.check_output(['xdg-user-dir', 'DESKTOP'], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        desktop = Path.home() / 'Desktop'
    desktop.mkdir(parents=True, exist_ok=True)
    # Desktop Entry usa aspas duplas e regras próprias de escape.
    def quote(value):
        return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
    entry = ('[Desktop Entry]\nType=Application\nName=Agenda de Contatos\n'
             f'Exec={quote(sys.executable)} {quote(destination / "agenda.py")}\n'
             'Icon=address-book-new\nTerminal=false\nCategories=Office;ContactManagement;\n')
    applications = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'applications'
    applications.mkdir(parents=True, exist_ok=True)
    for path in (desktop / 'agenda-contatos.desktop', applications / 'agenda-contatos.desktop'):
        path.write_text(entry, encoding='utf-8')
        path.chmod(0o755)
    print('Atalho criado em:', desktop / 'agenda-contatos.desktop')
    print('Se o sistema perguntar, escolha Permitir execução.')


if __name__ == '__main__':
    install()
