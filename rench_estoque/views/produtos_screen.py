import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from utils.database import get_db_connection

BG_COLOR = "#F0F2F5"; PRIMARY = "#1F5F8B"; DARK_TEXT = "#1A3A5C"
GRAY_TEXT = "#555555"; WHITE = "#FFFFFF"; LIGHT_BG = "#E5E8EC"
SUCCESS = "#1A6B3A"; DANGER = "#8B1A1A"; WARNING = "#E07B00"

class ProdutosScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        # --- Titulo + botoes topo
        top = tk.Frame(self, bg=BG_COLOR)
        top.pack(fill="x", padx=25, pady=(20,10))
        tk.Label(top, text="Cadastro de Produtos", font=("Arial", 24, "bold"), fg=DARK_TEXT, bg=BG_COLOR).pack(side="left")
        tk.Button(top, text="+ Novo Produto", bg=PRIMARY, fg=WHITE, bd=0, cursor="hand2",
                  font=("Arial", 11, "bold"), padx=15, pady=6, command=self.abrir_form).pack(side="right", padx=5)
        tk.Button(top, text="Exportar Excel", bg=LIGHT_BG, fg=DARK_TEXT, bd=0, cursor="hand2",
                  font=("Arial", 10), padx=15, pady=6, command=self.exportar).pack(side="right", padx=5)

        # --- Busca
        busca_row = tk.Frame(self, bg=BG_COLOR)
        busca_row.pack(fill="x", padx=25, pady=(0,10))
        self.entry_busca = ttk.Entry(busca_row, font=("Arial", 11), width=40)
        self.entry_busca.pack(side="left", ipady=4)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.carregar_dados())
        tk.Button(busca_row, text="🔍  Buscar", bg=PRIMARY, fg=WHITE, bd=0, cursor="hand2",
                  font=("Arial", 10, "bold"), padx=12, pady=4, command=self.carregar_dados).pack(side="left", padx=8)
        tk.Button(busca_row, text="⟳", bg=LIGHT_BG, fg=DARK_TEXT, bd=0, cursor="hand2",
                  font=("Arial", 12, "bold"), padx=6, pady=1, command=self.carregar_dados).pack(side="left")

        # --- Tabs
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=25, pady=(0,20))

        # Tab insumos
        self.frm_insumos = tk.Frame(tabs, bg=BG_COLOR)
        tabs.add(self.frm_insumos, text="  Insumos (Toner, Drum, etc)  ")
        self.tab_insumos(self.frm_insumos)

        # Tab equipamentos cadastrados
        self.frm_equip = tk.Frame(tabs, bg=BG_COLOR)
        tabs.add(self.frm_equip, text="  Equipamentos Cadastrados  ")
        self.tab_equip(self.frm_equip)

        # Tab categorias
        self.frm_cat = tk.Frame(tabs, bg=BG_COLOR)
        tabs.add(self.frm_cat, text="  Categorias  ")
        self.tab_categorias(self.frm_cat)

        self.carregar_dados()

    # ============================================================
    # TREEVIEW HELPER
    # ============================================================
    def criar_treeview(self, parent, cols, widths):
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=28, font=("Arial", 10), background=WHITE, fieldbackground=WHITE)
        style.configure("Custom.Treeview.Heading", font=("Arial", 10, "bold"), background=PRIMARY, foreground=DARK_TEXT)

        tree = ttk.Treeview(parent, columns=cols, show="headings", style="Custom.Treeview")
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="center" if c != "Descricao" else "w")
        return tree

    # ============================================================
    # ABA INSUMOS
    # ============================================================
    def tab_insumos(self, parent):
        cols = ("Codigo", "Nome", "Marca", "Modelo Comp.", "Qtd Atual", "Minimo", "Maximo", "Local", "Categoria")
        widths = [80, 140, 100, 120, 80, 70, 70, 100, 120]
        self.tree_insumos = self.criar_treeview(parent, cols, widths)
        self.tree_insumos.pack(fill="both", expand=True, pady=(5,0))
        self.tree_insumos.bind("<Double-1>", lambda e: self.editar_selecionado(self.tree_insumos))

        # Scrollbar
        scrolly = ttk.Scrollbar(self.tree_insumos, orient="vertical", command=self.tree_insumos.yview)
        self.tree_insumos.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")

    # ============================================================
    # ABA EQUIPAMENTOS (no cadastro de produtos = cadastro tipo)
    # ============================================================
    def tab_equip(self, parent):
        cols = ("Patrimonio", "Nome", "Marca", "Modelo", "Ano", "Status", "Cliente", "Categoria")
        widths = [90, 140, 100, 110, 60, 90, 130, 110]
        self.tree_equip = self.criar_treeview(parent, cols, widths)
        self.tree_equip.pack(fill="both", expand=True, pady=(5,0))
        self.tree_equip.bind("<Double-1>", lambda e: self.editar_equip_selecionado())

        scrolly = ttk.Scrollbar(self.tree_equip, orient="vertical", command=self.tree_equip.yview)
        self.tree_equip.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")

    # ============================================================
    # ABA CATEGORIAS
    # ============================================================
    def tab_categorias(self, parent):
        top = tk.Frame(parent, bg=BG_COLOR)
        top.pack(fill="x", pady=(5,10))
        tk.Label(top, text="Nova Categoria:", bg=BG_COLOR, font=("Arial", 10, "bold")).pack(side="left")
        self.entry_nova_cat = ttk.Entry(top, font=("Arial", 10), width=25)
        self.entry_nova_cat.pack(side="left", padx=(5,5), ipady=3)
        self.combo_tipo_cat = ttk.Combobox(top, values=["insumo", "equipamento"], state="readonly", width=13)
        self.combo_tipo_cat.set("insumo")
        self.combo_tipo_cat.pack(side="left", padx=(5,0))
        tk.Button(top, text="+ Adicionar", bg=SUCCESS, fg=WHITE, bd=0, cursor="hand2",
                  font=("Arial", 10, "bold"), padx=10, pady=4, command=self.adicionar_categoria).pack(side="left", padx=(10,0))

        cols = ("ID", "Nome", "Tipo", "Descricao")
        widths = [50, 200, 120, 300]
        self.tree_cats = self.criar_treeview(parent, cols, widths)
        self.tree_cats.pack(fill="both", expand=True)

    # ============================================================
    # CARREGAR DADOS
    # ============================================================
    def carregar_dados(self):
        busca = self.entry_busca.get().strip()
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Insumos
            sql_ins = """
                SELECT p.codigo, p.nome, p.marca, p.modelo_compativel, p.quantidade_atual,
                       p.estoque_minimo, p.estoque_maximo, p.localizacao_interna, COALESCE(c.nome,'-')
                FROM produtos p LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.ativo=1 AND (p.codigo LIKE ? OR p.nome LIKE ? OR p.marca LIKE ? OR p.modelo_compativel LIKE ?)
            """
            like = f"%{busca}%"
            cur.execute(sql_ins, (like, like, like, like))
            rows = cur.fetchall()
            self.tree_insumos.delete(*self.tree_insumos.get_children())
            for r in rows:
                tag = "critico" if r["quantidade_atual"] is not None and r["estoque_minimo"] is not None and r["quantidade_atual"] < r["estoque_minimo"] else ""
                self.tree_insumos.insert("", "end", values=tuple(r), tags=(tag,))
            self.tree_insumos.tag_configure("critico", background="#FFE0E0", foreground=DANGER)

            # Equipamentos cadastrados
            sql_eq = """
                SELECT e.numero_patrimonio, e.nome, e.marca, e.modelo, e.ano_fabricacao, e.status,
                       COALESCE(c.razao_social,'-'), COALESCE(cat.nome,'-')
                FROM equipamentos e
                LEFT JOIN clientes c ON e.cliente_id = c.id
                LEFT JOIN categorias cat ON e.categoria_id = cat.id
                WHERE e.ativo=1 AND (e.nome LIKE ? OR e.numero_patrimonio LIKE ? OR e.numero_serie LIKE ?)
            """
            cur.execute(sql_eq, (like, like, like))
            rows = cur.fetchall()
            self.tree_equip.delete(*self.tree_equip.get_children())
            for r in rows:
                self.tree_equip.insert("", "end", values=tuple(r))

            # Categorias
            cur.execute("SELECT id, nome, tipo, descricao FROM categorias WHERE ativo=1 ORDER BY tipo, nome")
            rows = cur.fetchall()
            self.tree_cats.delete(*self.tree_cats.get_children())
            for r in rows:
                self.tree_cats.insert("", "end", values=tuple(r))

            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ============================================================
    # FORMULARIO DE CADASTRO
    # ============================================================
    def abrir_form(self, editar_id=None):
        self.janela_form = tk.Toplevel(self)
        self.janela_form.title("Novo Produto" if not editar_id else "Editar Produto")
        self.janela_form.geometry("650x580")
        self.janela_form.configure(bg=WHITE)
        self.janela_form.transient(self)
        self.janela_form.grab_set()

        tk.Label(self.janela_form, text="Novo Produto" if not editar_id else "Editar Produto",
                 font=("Arial", 18, "bold"), fg=DARK_TEXT, bg=WHITE).pack(pady=(15,10))

        form = tk.Frame(self.janela_form, bg=WHITE)
        form.pack(fill="both", expand=True, padx=30, pady=5)

        labels_entries = [
            ("Codigo*",      "entry_codigo",     20),
            ("Nome*",        "entry_nome",       35),
            ("Descricao",    "entry_descricao",  40),
            ("Marca",        "entry_marca",      20),
            ("Modelo",       "entry_modelo",     20),
            ("Modelo Compativel", "entry_compativel", 25),
            ("Fornecedor",   "entry_fornecedor", 25),
            ("Unidade",      "entry_unidade",    10, "UN"),
            ("Estoque Minimo", "entry_min",     10, "0"),
            ("Estoque Maximo", "entry_max",     10, "0"),
            ("Localizacao (prateleira/corredor)", "entry_local", 30),
        ]

        row = 0
        for item in labels_entries:
            lbl, nome_attr, width = item[0], item[1], item[2]
            default = item[3] if len(item) > 3 else ""
            tk.Label(form, text=lbl, font=("Arial", 9, "bold"), fg=DARK_TEXT, bg=WHITE, anchor="w")\
                .grid(row=row, column=0, sticky="w", pady=(8,0))
            e = ttk.Entry(form, font=("Arial", 10), width=width)
            e.grid(row=row, column=1, sticky="w", padx=(10,0), pady=(8,0), columnspan=2)
            e.insert(0, default)
            setattr(self, nome_attr, e)
            row += 1

        # Categoria (combobox)
        tk.Label(form, text="Categoria", font=("Arial", 9, "bold"), fg=DARK_TEXT, bg=WHITE, anchor="w")\
            .grid(row=row, column=0, sticky="w", pady=(8,0))
        self.cb_categoria = ttk.Combobox(form, state="readonly", width=25, font=("Arial", 10))
        self.cb_categoria.grid(row=row, column=1, sticky="w", padx=(10,0), pady=(8,0))
        row += 1

        # Codigo de barras
        tk.Label(form, text="Codigo de Barras", font=("Arial", 9, "bold"), fg=DARK_TEXT, bg=WHITE, anchor="w")\
            .grid(row=row, column=0, sticky="w", pady=(8,0))
        self.entry_barcode = ttk.Entry(form, font=("Arial", 10), width=30)
        self.entry_barcode.grid(row=row, column=1, sticky="w", padx=(10,0), pady=(8,0))
        tk.Button(form, text="Gerar QR Code", bg=PRIMARY, fg=WHITE, bd=0, cursor="hand2",
                  font=("Arial", 9), padx=8, pady=2, command=self.gerar_qr_form)\
            .grid(row=row, column=2, sticky="w", padx=5, pady=(8,0))
        row += 1

        # QR
        self.lbl_qr = tk.Label(form, bg=WHITE)
        self.lbl_qr.grid(row=row, column=0, columnspan=3, pady=(10,0))

        # Botoes
        btns = tk.Frame(self.janela_form, bg=WHITE)
        btns.pack(fill="x", padx=30, pady=15)
        tk.Button(btns, text="Salvar", bg=SUCCESS, fg=WHITE, bd=0, cursor="hand2", font=("Arial", 11, "bold"),
                  padx=25, pady=6, command=lambda: self.salvar_produto(editar_id)).pack(side="left", padx=(0,5))
        tk.Button(btns, text="Cancelar", bg=LIGHT_BG, fg=DARK_TEXT, bd=0, cursor="hand2", font=("Arial", 11),
                  padx=20, pady=6, command=self.janela_form.destroy).pack(side="left")

        self.carregar_categorias_combo()

        # Se editando, carregar dados
        if editar_id:
            self.carregar_dados_edicao(editar_id)

    def carregar_categorias_combo(self):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nome FROM categorias WHERE tipo='insumo' AND ativo=1 ORDER BY nome")
            rows = cur.fetchall()
            self.cb_categoria["values"] = [f"{r['id']} - {r['nome']}" for r in rows]
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def gerar_qr_form(self):
        from views.login_screen import criar_qr_code
        codigo = self.entry_codigo.get().strip()
        if not codigo:
            messagebox.showwarning("Aviso", "Preencha o codigo primeiro.")
            return
        img = criar_qr_code(codigo, 120)
        self.lbl_qr.config(image=img)
        self.lbl_qr.image = img  # manter referencia

    def salvar_produto(self, editar_id=None):
        dados = {
            "codigo": self.entry_codigo.get().strip(),
            "nome": self.entry_nome.get().strip(),
            "descricao": self.entry_descricao.get().strip(),
            "marca": self.entry_marca.get().strip(),
            "modelo": self.entry_modelo.get().strip(),
            "modelo_compativel": self.entry_compativel.get().strip(),
            "fornecedor": self.entry_fornecedor.get().strip(),
            "unidade": self.entry_unidade.get().strip() or "UN",
            "estoque_minimo": int(self.entry_min.get() or 0),
            "estoque_maximo": int(self.entry_max.get() or 0),
            "localizacao_interna": self.entry_local.get().strip(),
            "codigo_barras": self.entry_barcode.get().strip(),
        }
        cat_sel = self.cb_categoria.get()
        categoria_id = int(cat_sel.split(" - ")[0]) if " - " in cat_sel else None

        if not dados["codigo"] or not dados["nome"]:
            messagebox.showwarning("Aviso", "Codigo e Nome sao obrigatorios.")
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            if editar_id:
                fields = []
                vals = []
                for k, v in dados.items():
                    fields.append(f"{k}=?")
                    vals.append(v)
                vals.append(categoria_id); vals.append(editar_id)
                cur.execute(f"UPDATE produtos SET {','.join(fields)}, categoria_id=? WHERE id=?", vals)
            else:
                cur.execute("""
                    INSERT INTO produtos (codigo, nome, descricao, categoria_id, marca, modelo, modelo_compativel, fornecedor, unidade,
                                          estoque_minimo, estoque_maximo, localizacao_interna, codigo_barras)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (dados["codigo"], dados["nome"], dados["descricao"], categoria_id, dados["marca"], dados["modelo"],
                      dados["modelo_compativel"], dados["fornecedor"], dados["unidade"], dados["estoque_minimo"],
                      dados["estoque_maximo"], dados["localizacao_interna"], dados["codigo_barras"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Produto salvo com sucesso!")
            self.janela_form.destroy()
            self.carregar_dados()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def carregar_dados_edicao(self, prod_id):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""SELECT * FROM produtos WHERE id=?""", (prod_id,))
            p = cur.fetchone()
            conn.close()
            if p:
                self.entry_codigo.insert(0, p["codigo"]); self.entry_codigo.config(state="readonly")
                self.entry_nome.insert(0, p["nome"] or "")
                self.entry_descricao.insert(0, p["descricao"] or "")
                self.entry_marca.insert(0, p["marca"] or "")
                self.entry_modelo.insert(0, p["modelo"] or "")
                self.entry_compativel.insert(0, p["modelo_compativel"] or "")
                self.entry_fornecedor.insert(0, p["fornecedor"] or "")
                self.entry_unidade.insert(0, p["unidade"] or "UN")
                self.entry_min.insert(0, str(p["estoque_minimo"] or 0))
                self.entry_max.insert(0, str(p["estoque_maximo"] or 0))
                self.entry_local.insert(0, p["localizacao_interna"] or "")
                self.entry_barcode.insert(0, p["codigo_barras"] or "")
                if p["categoria_id"]:
                    for v in self.cb_categoria["values"]:
                        if v.startswith(str(p["categoria_id"]) + " -"):
                            self.cb_categoria.set(v)
                            break
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def editar_selecionado(self, tree):
        sel = tree.selection()
        if not sel:
            return
        item = tree.item(sel[0])
        codigo = item["values"][0]
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM produtos WHERE codigo=?", (codigo,))
            row = cur.fetchone()
            conn.close()
            if row:
                self.abrir_form(row["id"])
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def editar_equip_selecionado(self):
        sel = self.tree_equip.selection()
        if not sel:
            return
        item = self.tree_equip.item(sel[0])
        pat = item["values"][0]
        messagebox.showinfo("Dica", f"Editar equipamento {pat} - funcionalidade em desenvolvimento.")

    def adicionar_categoria(self):
        nome = self.entry_nova_cat.get().strip()
        tipo = self.combo_tipo_cat.get()
        if not nome:
            messagebox.showwarning("Aviso", "Informe o nome da categoria.")
            return
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO categorias (nome, tipo, descricao) VALUES (?, ?, ?)", (nome, tipo, ""))
            conn.commit(); conn.close()
            self.entry_nova_cat.delete(0, "end")
            self.carregar_dados()
            messagebox.showinfo("Sucesso", "Categoria adicionada!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def exportar(self):
        messagebox.showinfo("Exportar", "Exportacao para Excel sera implementada em breve.")
