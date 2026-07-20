import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import hashlib
import json

from utils.database import get_db_connection
from views.login_screen import LoginScreen

def main():
    root = tk.Tk()
    root.title("RENCH Solucoes - Controle de Estoque")
    root.geometry("1280x750")
    root.configure(bg="#F0F0F0")
    try:
        root.state("zoomed")
    except:
        pass
    LoginScreen(root)
    root.mainloop()

if __name__ == "__main__":
    main()
