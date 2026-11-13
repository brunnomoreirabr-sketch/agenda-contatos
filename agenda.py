"""Ponto de entrada da aplicação."""
import tkinter as tk
from tkinter import messagebox
from agenda.ui import AgendaApp


def main():
    root = tk.Tk()
    root.withdraw()
    try:
        AgendaApp(root)
    except Exception as error:
        messagebox.showerror('Não foi possível abrir a agenda', str(error), parent=root)
        root.destroy()
        return
    root.deiconify()
    root.mainloop()


if __name__ == '__main__':
    main()
