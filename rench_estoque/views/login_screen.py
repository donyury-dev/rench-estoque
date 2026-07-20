import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw
from datetime import datetime
import hashlib
import json
import qrcode
from io import BytesIO

from utils.database import get_db_connection

# ================================================================
# CORES E ESTILO
# ================================================================
BG_COLOR       = "#F0F2F5"
PRIMARY_COLOR  = "#1F5F8B"
SECONDARY      = "#2E6DA4"
ACCENT_COLOR   = "#E07B00"
LIGHT_BLUE     = "#D5E8F0"
WHITE          = "#FFFFFF"
DARK_TEXT      = "#1A3A5C"
GRAY_TEXT      = "#555555"
LIGHT_GRAY     = "#E5E8EC"
SUCCESS        = "#1A6B3A"
DANGER         = "#8B1A1A"
WARNING        = "#E07B00"

# ================================================================
# HELPER: criar QR Code como PhotoImage
# ================================================================
def criar_qr_code(dados, tamanho=150):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(dados)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((tamanho, tamanho), Image.LANCZOS)
    return ImageTk.PhotoImage(img)

# ================================================================
# HELPER: criar ícone de fechar (X)
# ================================================================
def criar_icone_x(size=12, color="white"):
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.line([(2,2), (size-2, size-2)], fill=color, width=2)
    draw.line([(size-2,2), (2, size-2)], fill=color, width=2)
    return ImageTk.PhotoImage(img)

# ================================================================
# TELA DE LOGIN
# ================================================================
class LoginScreen:
    def __init__(self, root):
        self.root = root
        self.frame = tk.Frame(root, bg=PRIMARY_COLOR)
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Painel esquerdo com branding
        left = tk.Frame(self.frame, bg=PRIMARY_COLOR)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="RENCH", font=("Arial", 48, "bold"), fg=WHITE, bg=PRIMARY_COLOR).pack(anchor="w", padx=60, pady=(180,0))
        tk.Label(left, text="Solucoes em Tecnologia", font=("Arial", 20), fg=LIGHT_BLUE, bg=PRIMARY_COLOR).pack(anchor="w", padx=60)
        tk.Label(left, text="Sistema de Controle de Estoque\ne Rastreamento de Equipamentos", font=("Arial", 13), fg="#A0C8E0", bg=PRIMARY_COLOR, justify="left").pack(anchor="w", padx=60, pady=(20,0))

        # Painel direito com formulario
        right = tk.Frame(self.frame, bg=WHITE, width=420)
        right.pack(side="right", fill="y", padx=0)
        right.pack_propagate(False)

        inner = tk.Frame(right, bg=WHITE)
        inner.pack(expand=True, pady=40)

        tk.Label(inner, text="Bem-vindo", font=("Arial", 28, "bold"), fg=DARK_TEXT, bg=WHITE).pack(pady=(0,5))
        tk.Label(inner, text="Entre com suas credenciais", font=("Arial", 11), fg=GRAY_TEXT, bg=WHITE).pack(pady=(0,30))

        tk.Label(inner, text="Usuario", font=("Arial", 10, "bold"), fg=DARK_TEXT, bg=WHITE, anchor="w").pack(fill="x", padx=5, pady=(10,2))
        self.usuario = ttk.Entry(inner, width=30, font=("Arial", 12))
        self.usuario.pack(fill="x", padx=5, ipady=5)
        self.usuario.insert(0, "admin")

        tk.Label(inner, text="Senha", font=("Arial", 10, "bold"), fg=DARK_TEXT, bg=WHITE, anchor="w").pack(fill="x", padx=5, pady=(15,2))
        self.senha = ttk.Entry(inner, width=30, font=("Arial", 12), show="*")
        self.senha.pack(fill="x", padx=5, ipady=5)
        self.senha.insert(0, "admin123")

        btn = tk.Button(inner, text="Entrar", bg=PRIMARY_COLOR, fg=WHITE, font=("Arial", 12, "bold"), bd=0, cursor="hand2", command=self.fazer_login)
        btn.pack(fill="x", padx=5, pady=(30,10), ipady=8)

        tk.Label(inner, text="Usuario padrao: admin  |  Senha: admin123", font=("Arial", 9), fg=GRAY_TEXT, bg=WHITE).pack(pady=(5,0))

        self.root.bind("<Return>", lambda e: self.fazer_login())

    def fazer_login(self):
        usuario = self.usuario.get().strip()
        senha = self.senha.get().strip()
        if not usuario or not senha:
            messagebox.showwarning("Aviso", "Preencha usuario e senha.")
            return
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            hash_senha = hashlib.sha256(senha.encode()).hexdigest()
            cur.execute("SELECT id, nome, nivel_acesso FROM usuarios WHERE usuario=? AND senha_hash=? AND ativo=1", (usuario, hash_senha))
            user = cur.fetchone()
            conn.close()
            if user:
                self.frame.destroy()
                from views.main_screen import MainScreen
                MainScreen(self.root, {"id": user["id"], "nome": user["nome"], "nivel_acesso": user["nivel_acesso"]})
            else:
                messagebox.showerror("Erro", "Usuario ou senha incorretos.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))
