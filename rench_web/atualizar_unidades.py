import pandas as pd
import unicodedata

src = r'C:\Users\Kaio\Downloads\UNIDADES CORREIAS SAMIR.xlsx'
out_xlsx = r'C:\Users\Kaio\Downloads\UNIDADES DEFINITIVAS SAMIR.xlsx'
out_csv = r'C:\Users\Kaio\Downloads\UNIDADES DEFINITIVAS SAMIR.csv'

df = pd.read_excel(src, header=1)
df.columns = ['unidade', 'endereço', 'numero', 'cidade', 'estado']

def n(x):
    if pd.isnull(x): return x
    x = str(x).strip().upper()
    x = ''.join(c for c in unicodedata.normalize('NFKD', x) if unicodedata.category(c) != 'Mn')
    x = x.replace('.', '.').replace(',', ',').strip()
    return x

for col in df.columns:
    df[col] = df[col].apply(n)

df = df[df['unidade'] != 'UNIDADE'].op_duplicates().reset_index(drop=True)

# fix numero
def fix_num(x):
    if pd.isnull(x) or str(x).strip() == '': return ''
    s = str(x).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

df['numero'] = df['numero'].apply(fix_num)

# limpa adicional
df['unidade'] = df['unidade'].apply(lambda x: x.strip())
df['endereço'] = df['endereço'].apply(lambda x: x.strip())
df['cidade'] = df['cidade'].apply(lambda x: x.strip())
df['estado'] = df['estado'].apply(lambda x: x[:2] if len(x) > 2 else x)

# unidades com nome errado → corregir
completo = {
    'HD MBOI MIRIM': 'HOSP MBOI MIRIM',
    'HOSP MUN CUBATAO': 'HOSP MUN CUBATÃO',
    'HOSP MUN ITU': 'HOSP TAL ITU',
    'HOSP MUN NOVA ODESSA': 'HOSP NOVA ODESSA',
    'HOSP MUN QUISSAMA': 'HOSP MUN QUISSAMA',
    'HOSP N S NAZARETH': 'HOSP NAZARETH',
    'HOSP REGIONAL JUST LUZ': 'HOSP REGIONAL JUST LUZ',
    'HOSP REGIONAL VILHENA': 'HOSP REGIONAL VILHENA',
}
df['unidade'] = df['unidade'].replace(completo)

# prenucao por unidade (variações de umsma unidade)
prenucao = {
    'AME CARAPICUIBA': 'AME CARAPICUIBA',
    'AME DR JOSE ZENEDIN': 'AME DR JOSE ZENEDIN',
    'HOSP BENEF PORTUGUESA': 'HOSP PORTUGUESA',
    'HOSP CARIDADE ANITA COSTA': 'HOSP ANITA COSTA',
    'HOSP HENRIQUE BUCCOLINE': 'HOSP HENRIQUE BUCCOLINE',
    'HOSP MATERNO INFANTIL': 'HOSP MATERNO INFANTIL',
    'HOSP MUN AMERICANA': 'HOSP AMERICANA',
    'HOSP MUN CACHOEIRAS MACACU': 'HOSP CACHOEIRAS MACACU',
    'HOSP MUN CAJAMAR': 'HOSP CAJAMAR',
    'HOSP NAZARETH': 'HOSP NAZARETH',
    'HOSP REGIONAL CAMPO MAIOR': 'HOSP REGIONAL CAMPO MAIOR',
    'HOSP REGIONAL JUST LUZ': 'HOSP REGIONAL JUST LUZ',
    'HOSP REGIONAL VILHENA': 'HOSP REGIONAL VILHENA',
    'PA CACHOEIRA PAULISTA': 'PA CACHOEIRA PAULISTA',
    'POLICLINICA SAQUAREMA': 'POLICLINICA SAQUAREMA',
    'PS MIRACATU': 'PS MIRACATU',
    'PS PINDAMONHANGABA': 'PS PINDAMONHANGABA',
    'PU JACONE': 'PU JACONE',
    'PU SAMPAIO CORREA': 'PU SAMPAIO CORREA',
    'PU SAQUAREMA': 'PU SAQUAREMA',
    'STA CASA CHAVANTES': 'STA CASA CHAVANTES',
    'UPA CACHOEIRAS MACACU': 'UPA CACHOEIRAS MACACU',
    'UPA CARAPINA DA SERRA': 'UPA CARAPINA DA SERRA',
    'UPA DONA ROSA': 'UPA DONA ROSA',
    'UPA DR THELMO A CRUZ': 'UPA DR THELMO A CRUZ',
    'UPA JD ANGELA': 'UPA JD ANGELA',
    'UPA JORDANESIA': 'UPA JORDANESIA',
    'UPA SAN MARINO': 'UPA SAN MARINO',
    'UPA SAO DIMAS': 'UPA SAO DIMAS',
    'UPA VERA CRUZ': 'UPA VERA CRUZ',
}
df['unidade'] = df['unidade'].replace(prenucao)

with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='UNIDADES', index=False)
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

df.to_csv(out_csv, index=False, encoding='utf-8-sig')
print('SALVO:', out_xlsx)
print('CSV:', out_csv);
print('REGISTROS:', len(df));
print(df.to_string())