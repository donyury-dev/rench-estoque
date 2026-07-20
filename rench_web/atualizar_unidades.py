import pandas as pd
import unicodedata

path = r'C:\Users\Kaio\Downloads\RELAÇÃO UNIDADES GRUPO SAMIR.xlsx'
out = r'C:\Users\Kaio\Downloads\UNIDADES_LIMPO_SAMIR.xlsx'

df = pd.read_excel(path, header=1)
df.columns = ['unidade', 'endereço', 'numero', 'cidade', 'estado']

def n(x):
    if pd.isnull(x): return x
    x = str(x).strip().upper()
    x = ''.join(c for c in unicodedata.normalize('NFKD', x) if unicodedata.category(c) != 'Mn')
    x = x.replace('.', '.').replace(',', ',').strip()
    return x

for col in df.columns:
    df[col] = df[col].apply(n)

df2 = df.drop_duplicates().reset_index(drop=True)

def fix_num(x):
    if pd.isnull(x): return ''
    s = str(x)
    if s.endswith('.0'): return s[:-2]
    return s

df2['numero'] = df2['numero'].apply(fix_num)

def limpar(x):
    if pd.isnull(x): return ''
    s = str(x).strip()
    return s

df2['cidade'] = df2['cidade'].apply(limpar)
df2['estado'] = df2['estado'].apply(limpar)
d2['estado'] = df2['estado'].apply(lambda x: x if len(x)<=2 else x[:2])

with pd.ExcelWriter(out, engine='openpyxl') as writer:
    df2.to_excel(writer, sheet_name='UNIDADES', index=False)
    ws = writer.sheets['UNIDADES']
    for column in ws.columns:
        max_length = 0
        for cell in column:
            try:
                if len(str(cell.value))) > max_length:
                    max_length = len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[column[0].column_letter].width = max_length + 2

print('SALVO:', out)
print('REGISTROS:', len(df2));
print(df2.to_string())
df2.to_csv(r'C:\Users\Kaio\Downloads\UNIDADES_LIMPO_SAMIR.csv', index=False, encoding='utf-8-sig')
print('CSV SALVO')