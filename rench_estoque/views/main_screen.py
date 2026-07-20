import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw

from utils.database import get_db_connection
import views.login_screen as login

BG_COLOR      = "#F5F6FA"
PRIMARY       = "#1F5F8B"
PRIMARY_HOVER = "#164A6F"
LIGHT_BG      = "#E8EDF2"
WHITE         = "#FFFFFF"
DARK_TEXT     = "#1A3A5C"
GRAY_TEXT     = "#555555"
ACCENT        = "#E07B00"
SUCCESS       = "#1A6B3A"
DANGER        = "#8B1A1A"

# ================================================================
# MENU LATERAL
# ================================================================
class MenuLateral(tk.Frame):
    def __init__(self, parent, on_select, usuario):
        super().__init__(parent, bg=PRIMARY, width=250)
        self.pack(side="left", fill="y", padx=0, pady=0)
        self.pack_propagate(False)
        self.on_select = on_select

        self.icon_cache = {}

        # -- Logotipo / nome empresa
        tk.Label(self, text="RENCH", font=("Arial", 22, "bold"), fg=WHITE, bg=PRIMARY).pack(pady=(20,0))
        tk.Label(self, text="Controle de Estoque", font=("Arial", 10), fg="#A0C8E0", bg=PRIMARY).pack(pady=(0,20))

        self.itens_menu = [
            ("Dashboard",        self.icone_dashboard,  "dashboard"),
            ("Produtos",         self.icone_box,        "produtos"),
            ("Equipamentos",     self.icone_pc,         "equipamentos"),
            ("Estoque Interno",  self.icone_warehouse,  "estoque"),
            ("Clientes",         self.icone_user,       "clientes"),
            ("Locacoes",         self.icone_map,        "locacoes"),
            ("Ordens Servico",   self.icone_wrench,     "os"),
            ("Fornecedores",     self.icone_truck,      "fornecedores"),
            ("Relatorios",       self.icone_chart,      "relatorios"),
            ("Configuracoes",    self.icone_gear,       "config"),
        ]

        self.botoes = {}
        for nome, icon_func, chave in self.itens_menu:
            btn = tk.Button(self, text=f"  {nome}", font=("Arial", 11), fg=WHITE, bg=PRIMARY,
                            activebackground=PRIMARY_HOVER, activeforeground=WHITE,
                            bd=0, cursor="hand2", anchor="w", padx=20, pady=10,
                            command=lambda c=chave: self.selecionar(c))
            btn.pack(fill="x", padx=0, pady=0)
            self.botoes[chave] = btn

        # -- Usuario logado
        tk.Frame(self, bg="#154A70", height=2).pack(fill="x", pady=(20,10))
        tk.Label(self, text=f"Logado:\n{usuario['nome']}", font=("Arial", 10),
                 fg=WHITE, bg=PRIMARY, justify="center", wraplength=230).pack(padx=10)
        tk.Button(self, text="Sair", font=("Arial", 10), fg=WHITE, bg=DANGER,
                  bd=0, cursor="hand2", command=self.sair).pack(fill="x", padx=20, pady=10)

        self.selecionar("dashboard")

    def selecionar(self, chave):
        for k, btn in self.botoes.items():
            if k == chave:
                btn.config(bg=PRIMARY_HOVER, font=("Arial", 11, "bold"))
            else:
                btn.config(bg=PRIMARY, font=("Arial", 11))
        self.on_select(chave)

    def sair(self):
        if messagebox.askyesno("Sair", "Deseja realmente sair do sistema?"):
            self.master.destroy()

    # mini-icones usando PIL draw
    def _criar_icone(self, draw_fn, size=(20,20)):
        img = Image.new("RGBA", size, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw_fn(draw, size)
        return ImageTk.PhotoImage(img)
    def icone_dashboard(self): pass
    def icone_box(self): pass
    def icone_pc(self): pass
    def icone_warehouse(self): pass
    def icone_user(self): pass
    def icone_map(self): pass
    def icone_wrench(self): pass
    def icone_truck(self): pass
    def icone_chart(self): pass
    def icone_gear(self): pass

# ================================================================
# CONTEUDO DAS TELAS (PLUGS - vamos criar cada um separadamente)
# ================================================================
class DashboardFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(self, text="Dashboard", font=("Arial", 28, "bold"), fg=DARK_TEXT, bg=BG_COLOR).pack(anchor="nw", padx=30, pady=(25,10))

        # Cards de resumo
        self.frame_cards = tk.Frame(self, bg=BG_COLOR)
        self.frame_cards.pack(fill="x", padx=30, pady=10)

        self.carregar_dados()

    def criar_card(self, parent, titulo, valor, cor, icon_char):
        card = tk.Frame(parent, bg=WHITE, bd=0, relief="flat", highlightthickness=0)
        card.pack(side="left", fill="both", expand=True, padx=5)
        for c in ["<Enter>", "<Leave>"]:
            card.bind(c, lambda e, w=card: w.config(bg=LIGHT_BG if e.type=="7" else WHITE))

        tk.Label(card, text=icon_char, font=("Arial", 28), fg=cor, bg=WHITE).pack(anchor="w", padx=15, pady=(12,0))
        tk.Label(card, text=valor, font=("Arial", 28, "bold"), fg=DARK_TEXT, bg=WHITE).pack(anchor="w", padx=15, pady=(5,0))
        tk.Label(card, text=titulo, font=("Arial", 11), fg=GRAY_TEXT, bg=WHITE).pack(anchor="w", padx=15, pady=(0,12))
        return card

    def carregar_dados(self):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Total produtos
            cur.execute("SELECT COUNT(*) FROM produtos WHERE ativo=1")
            total_produtos = cur.fetchone()[0]
            # Total equipamentos
            cur.execute("SELECT COUNT(*) FROM equipamentos WHERE ativo=1")
            total_equip = cur.fetchone()[0]
            # Equipamentos locados
            cur.execute("SELECT COUNT(*) FROM equipamentos WHERE status='locado' AND ativo=1")
            total_locados = cur.fetchone()[0]
            # Produtos abaixo do minimo
            cur.execute("SELECT COUNT(*) FROM produtos WHERE quantidade_atual < estoque_minimo AND ativo=1")
            total_criticos = cur.fetchone()[0]
            # Total clientes
            cur.execute("SELECT COUNT(*) FROM clientes WHERE ativo=1")
            total_clientes = cur.fetchone()[0]
            # OS abertas
            cur.execute("SELECT COUNT(*) FROM ordens_servico WHERE status IN ('aberta','em_andamento','aguardando_peca')")
            total_os = cur.fetchone()[0]
            conn.close()
        except Exception:
            total_produtos = total_equip = total_locados = total_criticos = total_clientes = total_os = 0

        for w in self.frame_cards.winfo_children():
            w.destroy()

        self.criar_card(self.frame_cards, "Produtos Cadastrados", str(total_produtos), PRIMARY, "📦")
        self.criar_card(self.frame_cards, "Equipamentos Totais", str(total_equip), PRIMARY, "🖨️")
        self.criar_card(self.frame_cards, "Equipamentos Locados", str(total_locados), ACCENT, "📍")
        self.criar_card(self.frame_cards, "Itens em Estoque Critico", str(total_criticos), DANGER, "⚠️")
        self.criar_card(self.frame_cards, "Clientes", str(total_clientes), SUCCESS, "👥")
        self.criar_card(self.frame_cards, "OS em Aberto", str(total_os), WARNING, "🔧")

# ================================================================
# TELA PRINCIPAL
# ================================================================
class MainScreen:
    def __init__(self, root, usuario):
        self.root = root
        self.usuario = usuario
        self.root.title(f"RENCH Estoque - {usuario['nome']} ({usuario['nivel_acesso']})")
        self.root.configure(bg=BG_COLOR)
        for w in self.root.winfo_children():
            w.destroy()

        # -- Menu lateral
        self.menu = MenuLateral(self.root, self.trocar_tela, usuario)

        # -- Container do conteudo
        self.container = tk.Frame(self.root, bg=BG_COLOR)
        self.container.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        self.tela_atual = None
        self.trocar_tela("dashboard")

    def trocar_tela(self, chave):
        if self.tela_atual:
            self.tela_atual.destroy()

        # Importacao dinamica das views
        if chave == "dashboard":
            self.tela_atual = DashboardFrame(self.container)
        elif chave == "produtos":
            from views.produtos_screen import ProdutosScreen
            self.tela_atual = ProdutosScreen(self.container)
        elif chave == "equipamentos":
            from views.equipamentos_screen import EquipamentosScreen
            self.tela_atual = EquipamentosScreen(self.container)
        elif chave == "estoque":
            from views.estoque_screen import EstoqueScreen
            self.tela_atual = EstoqueScreen(self.container)
        elif chave == "clientes":
            from views.clientes_screen import ClientesScreen
            self.tela_atual = ClientesScreen(self.container)
        elif chave == "locacoes":
            from views.locacoes_screen import LocacoesScreen
            self.tela_atual = LocacoesScreen(self.container)
        elif chave == "os":
            from views.os_screen import OSScreen
            self.tela_atual = OSScreen(self.container)
        elif chave == "fornecedores":
            from views.fornecedores_screen import FornecedoresScreen
            self.tela_atual = FornecedoresScreen(self.container)
        elif chave == "relatorios":
            from views.relatorios_screen import RelatoriosScreen
            self.tela_atual = RelatoriosScreen(self.container)
        else:
            self.tela_atual = tk.Frame(self.container, bg=BG_COLOR)
            self.tela_atual.place(relx=0, rely=0, relwidth=1, relheight=1)
            tk.Label(self.tela_atual, text="Em desenvolvimento...", font=("Arial", 20, "bold"),
                     fg=GRAY_TEXT, bg=BG_COLOR).pack(expand=True)

        if chave == "dashboard":
            self.tela_atual.carregar_dados()
