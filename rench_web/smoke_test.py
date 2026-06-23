from app import app

c = app.test_client()

# Teste 1: Lista sem filtro
resp = c.get('/equipamentos')
assert resp.status_code == 200, f"Falha: {resp.status_code}"
html = resp.data.decode('utf-8','replace')
assert 'Última mov.' in html, "Coluna nao encontrada"
assert 'Com movimento nos' in html, "Filtro nao encontrado"
print("[OK] /equipamentos renderiza corretamente")

# Teste 2: Com filtro mov_recente=30d
resp = c.get('/equipamentos?mov_recente=30d')
assert resp.status_code == 200
print("[OK] /equipamentos?mov_recente=30d - sem erro")

# Teste 3: Botao Movimentar existe
assert 'href="/movimentar/' in html
print("[OK] Botao Movimentar presente na lista")

# Teste 4: Tela de movimentar abre
resp = c.get('/movimentar/2')
assert resp.status_code == 200
html_mov = resp.data.decode('utf-8','replace')
assert 'Registrar nova movimentacao' in html_mov
print("[OK] /movimentar/2 abre corretamente")

print("\nTodos os testes passaram! Sistema pronto para uso.")
