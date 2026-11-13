"""Interface de desktop, construída com Tkinter e ttk."""
import csv
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
from .storage import ContactStore, FIELDS

BG = '#f3f5f7'
INK = '#172b3a'
MUTED = '#627585'
GREEN = '#206a55'


class AgendaApp:
    def __init__(self, root, store=None):
        self.root = root
        self.store = store or ContactStore()
        self.selected_id = None
        self.baseline = ('', '', '', '')
        self.refreshing = False
        self.root.title('Agenda de contatos')
        self.root.geometry('1120x820')
        self.root.minsize(960, 780)
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self._styles()
        self._build()
        self.refresh()
        self.root.bind('<Control-n>', lambda event: self.new_contact())
        self.root.bind('<Control-s>', lambda event: self.save())
        self.root.bind('<Control-f>', lambda event: self.search_entry.focus_set())

    def _styles(self):
        families = {name.casefold(): name for name in tkfont.families(self.root)}
        self.font_family = next((families[name.casefold()] for name in ('Segoe UI', 'Helvetica', 'Arial')
                                 if name.casefold() in families), 'TkDefaultFont')
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=(self.font_family, 11), background=BG, foreground=INK)
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background='white')
        style.configure('Card.TLabel', background='white')
        style.configure('Title.TLabel', font=(self.font_family, 25, 'bold'))
        style.configure('Muted.TLabel', foreground=MUTED)
        style.configure('Panel.TLabel', background='white', font=(self.font_family, 16, 'bold'))
        style.configure('TButton', padding=(14, 9), background='#e8edef', borderwidth=0)
        style.map('TButton', background=[('active', '#dae3e7')])
        style.configure('Primary.TButton', background=GREEN, foreground='white')
        style.map('Primary.TButton', background=[('active', '#185340')])
        style.configure('Danger.TButton', foreground='#a23b36')
        style.configure('TEntry', padding=9, fieldbackground='white')
        style.configure('Treeview', rowheight=43, background='white', fieldbackground='white', borderwidth=0)
        style.configure('Treeview.Heading', font=(self.font_family, 10, 'bold'), padding=(10, 12), background='#e9eff1')
        style.map('Treeview', background=[('selected', '#dceee7')], foreground=[('selected', INK)])

    def _build(self):
        wrapper = ttk.Frame(self.root, padding=28)
        wrapper.pack(fill='both', expand=True)
        heading = ttk.Frame(wrapper)
        heading.pack(fill='x')
        texts = ttk.Frame(heading)
        texts.pack(side='left')
        ttk.Label(texts, text='Agenda de contatos', style='Title.TLabel').pack(anchor='w')
        ttk.Label(texts, text='Seus contatos, sempre por perto.', style='Muted.TLabel').pack(anchor='w', pady=(5, 0))
        ttk.Button(heading, text='+ Novo contato', style='Primary.TButton', command=self.new_contact).pack(side='right')
        toolbar = ttk.Frame(wrapper)
        toolbar.pack(fill='x', pady=(25, 18))
        self.query = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.query, width=35)
        self.search_entry.pack(side='left')
        ttk.Label(toolbar, text='Buscar contatos', style='Muted.TLabel').pack(side='left', padx=12)
        self.query.trace_add('write', lambda *_: self.refresh())
        ttk.Button(toolbar, text='Exportar CSV', command=self.export_csv).pack(side='right')
        ttk.Button(toolbar, text='Importar CSV', command=self.import_csv).pack(side='right', padx=(0, 8))
        body = ttk.Frame(wrapper)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=330)
        body.rowconfigure(0, weight=1)
        listing = ttk.Frame(body, style='Card.TFrame')
        listing.grid(row=0, column=0, sticky='nsew', padx=(0, 20))
        self.count = ttk.Label(listing, style='Card.TLabel', padding=(16, 16))
        self.count.pack(anchor='w')
        table = ttk.Frame(listing, style='Card.TFrame')
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('nome', 'telefone'), show='headings', selectmode='browse')
        self.tree.heading('nome', text='NOME', anchor='w')
        self.tree.heading('telefone', text='TELEFONE', anchor='w')
        self.tree.column('nome', width=220, minwidth=140)
        self.tree.column('telefone', width=160, minwidth=120)
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(side='left', fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select_contact)
        self.empty = ttk.Label(listing, text='', style='Card.TLabel', padding=16, foreground=MUTED)
        self.empty.pack(fill='x')
        editor = ttk.Frame(body, padding=22, style='Card.TFrame')
        editor.grid(row=0, column=1, sticky='nsew')
        self.form_title = ttk.Label(editor, text='Novo contato', style='Panel.TLabel')
        self.form_title.pack(anchor='w', pady=(0, 18))
        self.values = {}
        self.entries = {}
        for field, label in zip(FIELDS, ('Nome *', 'Telefone', 'E-mail', 'Endereço')):
            ttk.Label(editor, text=label, style='Card.TLabel').pack(anchor='w', pady=(8, 5))
            self.values[field] = tk.StringVar()
            entry = ttk.Entry(editor, textvariable=self.values[field], width=29)
            entry.pack(fill='x')
            self.entries[field] = entry
        ttk.Label(editor, text='* Campo obrigatório', style='Card.TLabel', foreground=MUTED).pack(anchor='w', pady=(12, 16))
        ttk.Button(editor, text='Salvar contato', style='Primary.TButton', command=self.save).pack(fill='x')
        self.delete_button = ttk.Button(editor, text='Excluir contato', style='Danger.TButton', command=self.delete)
        self.delete_button.pack(fill='x', pady=(8, 0))
        self.delete_button.state(['disabled'])
        footer = ttk.Frame(wrapper)
        footer.pack(side='bottom', fill='x', pady=(16, 0))
        self.status = ttk.Label(footer, text='Pronto para cadastrar seu primeiro contato.', style='Muted.TLabel')
        self.status.pack(side='left')
        ttk.Button(footer, text='Onde ficam meus dados?', command=self.show_data_path).pack(side='right')
        body.pack(fill='both', expand=True)

    def dirty(self):
        return tuple(self.values[f].get() for f in FIELDS) != self.baseline

    def can_discard(self):
        return not self.dirty() or messagebox.askyesno(
            'Alterações pendentes', 'Descartar as alterações que ainda não foram salvas?', parent=self.root)

    def fill(self, contact=None):
        self.selected_id = contact['id'] if contact else None
        for field in FIELDS:
            self.values[field].set(contact[field] if contact else '')
        self.baseline = tuple(self.values[f].get() for f in FIELDS)
        self.form_title.configure(text='Editar contato' if contact else 'Novo contato')
        self.delete_button.state(['!disabled'] if contact else ['disabled'])

    def refresh(self, select_id=None):
        self.refreshing = True
        rows = self.store.list(self.query.get())
        self.visible = {str(row['id']): row for row in rows}
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert('', 'end', iid=str(row['id']), values=(row['nome'], row['telefone'] or '—'))
        target = select_id if select_id is not None else self.selected_id
        if str(target) in self.visible:
            self.tree.selection_set(str(target))
            self.tree.see(str(target))
        total = len(self.store.list())
        self.count.configure(text=f'{len(rows)} de {total} contatos' if self.query.get() else f'{total} contato' + ('' if total == 1 else 's'))
        self.empty.configure(text=('Nenhum contato encontrado.' if self.query.get() else 'Sua agenda começa com um novo contato.') if not rows else '')
        self.refreshing = False

    def select_contact(self, event=None):
        if self.refreshing:
            return
        selected = self.tree.selection()
        if not selected or int(selected[0]) == self.selected_id:
            return
        if not self.can_discard():
            self.tree.selection_remove(*selected)
            if str(self.selected_id) in self.visible:
                self.tree.selection_set(str(self.selected_id))
            return
        self.fill(self.visible[selected[0]])

    def new_contact(self):
        if self.can_discard():
            self.tree.selection_remove(*self.tree.selection())
            self.fill()
            self.entries['nome'].focus_set()
            self.status.configure(text='Preencha os dados e clique em Salvar contato.')

    def save(self):
        try:
            contact_id = self.store.save({f: self.values[f].get() for f in FIELDS}, self.selected_id)
        except (ValueError, sqlite3.Error, OSError) as error:
            messagebox.showerror('Não foi possível salvar', str(error), parent=self.root)
            return
        self.fill(next(row for row in self.store.list() if row['id'] == contact_id))
        self.refresh(select_id=contact_id)
        self.status.configure(text='Contato salvo no computador.')

    def delete(self):
        if self.selected_id is None:
            return
        if not messagebox.askyesno('Excluir contato', f'Excluir “{self.values["nome"].get()}” da agenda?', parent=self.root):
            return
        try:
            self.store.delete(self.selected_id)
        except sqlite3.Error as error:
            messagebox.showerror('Não foi possível excluir', str(error), parent=self.root)
            return
        self.fill()
        self.refresh()
        self.status.configure(text='Contato excluído.')

    def import_csv(self):
        if not self.can_discard():
            return
        path = filedialog.askopenfilename(parent=self.root, title='Importar contatos', filetypes=[('Arquivo CSV', '*.csv')])
        if not path:
            return
        try:
            added, skipped = self.store.import_csv(path)
        except (OSError, ValueError, UnicodeError, csv.Error, sqlite3.Error) as error:
            messagebox.showerror('Não foi possível importar', str(error), parent=self.root)
            return
        self.fill()
        self.refresh()
        self.status.configure(text=f'Importação concluída: {added} adicionados; {skipped} repetidos ignorados.')

    def export_csv(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='Exportar todos os contatos salvos',
                                          defaultextension='.csv', initialfile='contatos.csv', filetypes=[('Arquivo CSV', '*.csv')])
        if not path:
            return
        try:
            self.store.export_csv(path)
        except (OSError, ValueError, sqlite3.Error) as error:
            messagebox.showerror('Não foi possível exportar', str(error), parent=self.root)
            return
        self.status.configure(text='Contatos exportados. Guarde o CSV como cópia de segurança.')

    def show_data_path(self):
        messagebox.showinfo('Seus dados', f'Os contatos são salvos automaticamente em:\n\n{self.store.path}\n\nUse Exportar CSV para fazer uma cópia de segurança.', parent=self.root)

    def close(self):
        if self.can_discard():
            self.store.close()
            self.root.destroy()
