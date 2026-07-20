import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox

from utils.database import get_db_connection

BG_COLOR = "#F0F2F5"; PRIMARY = "#1F5F8B"; DARK_TEXT = "#1A3A5C"
GRAY_TEXT = "#555555"; WHITE = "#FFFFFF"; LIGHT_BG = "#E5E8EC"
SUCCESS = "#1A6B3A"; DANGER = "#8B1A1A"; WARNING = "#E07B00"

class EquipamentosScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Titulo
        top = tk.Frame(self, bg=BG_COLOR)
        top.pack(fill="x", padx=25, pady=(20,10))
        tk.Label(top, text="Equipamentos", font=("Arial", 24, "bold"), fg=DARK_TEXT, bg=BG_COLOR).pack(side="left")
        tk.Button(top, text="+ Novo Equipamento", bg=PRIMARY, fg=WHITE, bd=0, cursor="hand2",
                  font=("Arial", 11, "bold"), padx=15, pady=6, command=self.abrir_form).pack(side="right", padx=5)

        # Filtros
        filtros = tk.Frame(self, bg=BG_COLOR)
        filtros.pack(fill="x", padx=25, pady=(0,5))
        tk.Label(filtros, text="Buscar:", bg=BG_COLOR, font=("Arial", 10, "bold")).pack(side="left")
        self.entry_busca = ttk.Entry(filtros, font=("Arial", 11), width=30)
        self.entry_busca.pack(side="left", padx=(5,10), ipady=4)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.carregar())
        tk.Label(filtros, text="Status:", bg=BG_COLOR, font=("Arial", 10, "bold")).pack(side="left")
        self.cb_status = ttk.Combobox(filtros, values=["Todos", "em_estoque", "locado", "em_manutencao", "descartado"],
                                      state="readonly", width=15, font=("Arial", 10))
        self.cb_status.set("Todos")
        self.cb_status.pack(side="left", padx=(5,10))
        self.cb_status.bind("<<ComboboxSelected>>", lambda e: self.carregar())
        tk.Button(filtros, text="Atualizar", bg=PRIMARY, fg=WHITE, bd=0, cursor="hand2",
                  font=("Arial", 10, "bold"), padx=12, pady=3, command=self.carregar).pack(side="left")

        # Treeview
        style = ttk.Style()
        style.configure("EQ.Treeview", rowheight=28, font=("Arial", 10))
        style.configure("EQ.Treeview.Heading", font=("Arial", 10, "bold"))
        tree_frame = tk.Frame(self, bg=BG_COLOR)
        tree_frame.pack(fill="both", expand=True, padx=25, pady=(5,20))

        cols = ("NS", "Patrimonio", "Nome", "Marca", "Modelo", "Ano", "Status", "Cliente", "Contrato")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="EQ.Treeview")
        widths = [120, 90, 160, 100, 120, 50, 90, 150, 100]
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrolly = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.editar())

        # Resumo
        self.lbl_resumo = tk.Label(self, text="", font=("Arial", 11, "bold"),
                                     fg=GRAY_TEXT, bg=BG_COLOR)
        self.lbl_resumo.pack(anchor="w", padx=25, pady=(0,10))

        self.carregar()

    def carregar(self):
        busca = self.entry_busca.get().strip()
        status = self.cb_status.get()
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            sql = """
                SELECT e.numero_serie, e.numero_patrimonio, e.nome, e.marca, e.modelo, e.ano_fabricacao,
                       e.status, COALESCE(c.razao_social,'—'), COALESCE(e.contrato,'—')
                FROM equipamentos e
                LEFT JOIN clientes c ON e.cliente_id = c.id
                WHERE e.ativo=1 AND (e.numero_serie LIKE ? OR e.nome LIKE ? OR e.numero_patrimonio LIKE ?)
            """
            params = [f"%{busca}%", f"%{busca}%", f"%{busca}%"]
            if status != "Todos":
                sql += " AND e.status=?"
                params.append(status)
            sql += " ORDER BY e.status, e.nome"
            cur.execute(sql, params)
            rows = cur.fetchall()
            self.tree.delete(*self.tree.get_children())
            cor_status = {"em_estoque": "#D6F0E0", "locado": "#D5E8F0", "em_manutencao": "#FFF3CD", "descartado": "#F8D7DA"}
            for r in rows:
                tag = r["status"]
                self.tree.insert("", "end", values=tuple(r), tags=(tag,))
            for st, cor in cor_status.items():
                self.tree.tag_configure(st, background=cor)
            # resumo
            cur.execute("SELECT status, COUNT(*) FROM equipamentos WHERE ativo=1 GROUP BY status")
            resumo = cur.fetchall()
            conn.close()
            texto = "  |  ".join([f"{r['status'].replace('_',' ')}: {r['COUNT(*)']}" for r in resumo])
            self.lbl_resumo.config(text=f"Resumo: {texto}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def abrir_form(self):
        messagebox.showinfo("Em andamento", "Formulario de cadastro de equipamentos sera implementado em breve.")

    def editar(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        ns = item["values"][0]
        messagebox.showinfo("Editar", f"Editar equipamento NS: {ns}\n\nFuncionalidade em desenvolvimento.")
