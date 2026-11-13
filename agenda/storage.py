"""Persistência local e intercâmbio de contatos em CSV."""
import csv
import os
import sqlite3
import sys
import unicodedata
from pathlib import Path

FIELDS = ('nome', 'telefone', 'email', 'endereco')


def data_directory():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'AgendaContatos'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'AgendaContatos'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'agenda-contatos'


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if unicodedata.category(c) != 'Mn')


class ContactStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_directory() / 'contatos.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.execute('''CREATE TABLE IF NOT EXISTS contatos (
                id INTEGER PRIMARY KEY, nome TEXT NOT NULL, telefone TEXT NOT NULL,
                email TEXT NOT NULL, endereco TEXT NOT NULL)''')

    @staticmethod
    def validate(values):
        cleaned = {field: str(values.get(field, '') or '').strip() for field in FIELDS}
        if not cleaned['nome']:
            raise ValueError('Preencha o nome do contato.')
        if cleaned['email'] and ('@' not in cleaned['email'] or ' ' in cleaned['email']):
            raise ValueError('Confira o e-mail informado.')
        return cleaned

    def list(self, query=''):
        rows = [dict(row) for row in self.connection.execute('SELECT * FROM contatos')]
        query = normalize(query.strip())
        return sorted((row for row in rows if query in normalize(' '.join(row[f] for f in FIELDS))),
                      key=lambda row: normalize(row['nome']))

    def save(self, values, contact_id=None):
        values = self.validate(values)
        with self.connection:
            if contact_id is None:
                result = self.connection.execute(
                    'INSERT INTO contatos (nome, telefone, email, endereco) VALUES (?, ?, ?, ?)',
                    tuple(values[f] for f in FIELDS))
                return result.lastrowid
            result = self.connection.execute(
                'UPDATE contatos SET nome=?, telefone=?, email=?, endereco=? WHERE id=?',
                (*[values[f] for f in FIELDS], contact_id))
            if result.rowcount != 1:
                raise ValueError('Este contato não existe mais. Atualize a lista.')
            return contact_id

    def delete(self, contact_id):
        with self.connection:
            self.connection.execute('DELETE FROM contatos WHERE id=?', (contact_id,))

    def import_csv(self, path):
        with open(path, encoding='utf-8-sig', newline='') as source:
            sample = source.read(4096)
            source.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(source, dialect=dialect)
            if not reader.fieldnames:
                raise ValueError('O arquivo CSV está vazio.')
            headers = {normalize(h.strip()): h for h in reader.fieldnames}
            aliases = {'nome': ('nome',), 'telefone': ('telefone',),
                       'email': ('email', 'e-mail'), 'endereco': ('endereco',)}
            columns = {field: next((headers[a] for a in names if a in headers), None)
                       for field, names in aliases.items()}
            if not all(columns.values()):
                raise ValueError('O CSV precisa das colunas: nome, telefone, email e endereco.')
            pending = []
            for row in reader:
                if None in row:
                    raise ValueError(f'Linha {reader.line_num}: há colunas extras no CSV.')
                if not any(value and value.strip() for value in row.values()):
                    continue
                try:
                    pending.append(self.validate({f: row[columns[f]] for f in FIELDS}))
                except ValueError as error:
                    raise ValueError(f'Linha {reader.line_num}: {error}') from error
        existing = {tuple(row[f] for f in FIELDS) for row in self.list()}
        added = skipped = 0
        with self.connection:
            for values in pending:
                key = tuple(values[f] for f in FIELDS)
                if key in existing:
                    skipped += 1
                    continue
                self.connection.execute(
                    'INSERT INTO contatos (nome, telefone, email, endereco) VALUES (?, ?, ?, ?)', key)
                existing.add(key)
                added += 1
        return added, skipped

    def export_csv(self, path):
        if Path(path).resolve() == self.path.resolve():
            raise ValueError('Escolha outro arquivo para não sobrescrever o banco da agenda.')
        with open(path, 'w', encoding='utf-8-sig', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows({f: row[f] for f in FIELDS} for row in self.list())

    def close(self):
        self.connection.close()
