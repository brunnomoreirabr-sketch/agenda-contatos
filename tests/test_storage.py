import csv
import tempfile
import unittest
from pathlib import Path
from agenda.storage import ContactStore


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.store = ContactStore(self.path / 'contatos.sqlite3')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def contact(self, **changes):
        return dict(nome='João Silva', telefone='(98) 99999-0101', email='joao@example.com', endereco='São Luís', **changes)

    def test_crud_persists_and_search_ignores_accents(self):
        key = self.store.save(self.contact())
        self.store.close()
        self.store = ContactStore(self.path / 'contatos.sqlite3')
        self.assertEqual(self.store.list('joao')[0]['id'], key)
        changed = self.contact()
        changed['telefone'] = '1234'
        self.store.save(changed, key)
        self.assertEqual(self.store.list('1234')[0]['id'], key)
        self.store.delete(key)
        self.assertEqual(self.store.list(), [])

    def test_export_import_round_trip_and_duplicates(self):
        self.store.save(self.contact())
        path = self.path / 'backup.csv'
        self.store.export_csv(path)
        self.assertEqual(self.store.import_csv(path), (0, 1))
        other = ContactStore(self.path / 'other.sqlite3')
        try:
            self.assertEqual(other.import_csv(path), (1, 0))
            self.assertEqual(other.list()[0]['endereco'], 'São Luís')
        finally:
            other.close()

    def test_import_validates_all_rows_before_writing(self):
        path = self.path / 'bad.csv'
        path.write_text('nome;telefone;e-mail;endereço\nMaria;123;maria@example.com;Centro\n;456;;Bairro\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Linha 3'):
            self.store.import_csv(path)
        self.assertEqual(self.store.list(), [])

    def test_semicolon_and_accented_headers(self):
        path = self.path / 'excel.csv'
        path.write_text('nome;telefone;e-mail;endereço\nMaria;001234;;Centro\n', encoding='utf-8-sig')
        self.assertEqual(self.store.import_csv(path), (1, 0))
        self.assertEqual(self.store.list()[0]['telefone'], '001234')

    def test_same_name_contacts_remain_independent(self):
        first = self.store.save(self.contact())
        second = self.store.save(self.contact())
        self.store.delete(first)
        self.assertEqual(self.store.list()[0]['id'], second)

    def test_invalid_name_and_database_overwrite_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save({'nome': ' '})
        with self.assertRaises(ValueError):
            self.store.export_csv(self.store.path)
        self.assertEqual(self.store.list(), [])


if __name__ == '__main__':
    unittest.main()
