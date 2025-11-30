import pandas as pd
import numpy as np

df = pd.read_csv('biofouling_report.csv')

print('='*70)
print('           INTERPRETACAO DO RELATORIO DE BIOINCRUSTACAO')
print('='*70)

# Visao geral
print(f'\n[VISAO GERAL]')
print(f'   Total de eventos: {len(df):,}')
print(f'   Navios na frota: {df["shipName"].nunique()}')
print(f'   Periodo: {df["startGMTDate"].min()[:10]} a {df["startGMTDate"].max()[:10]}')

# Distribuicao por classe
print(f'\n[DISTRIBUICAO POR CLASSIFICACAO]')
class_dist = df['bio_class'].value_counts()
for c in ['Leve', 'Moderada', 'Severa']:
    if c in class_dist.index:
        pct = 100 * class_dist[c] / len(df)
        print(f'   {c:12}: {class_dist[c]:,} eventos ({pct:.1f}%)')

# Estatisticas do Excess Ratio
print(f'\n[EXCESS RATIO (ER)]')
er = df['target_excess_ratio']
print(f'   Media:    {er.mean()*100:+.1f}%')
print(f'   Mediana:  {er.median()*100:+.1f}%')
print(f'   Minimo:   {er.min()*100:+.1f}%')
print(f'   Maximo:   {er.max()*100:+.1f}%')
neg_pct = 100 * (er < 0).sum() / len(er)
print(f'   ER < 0:   {neg_pct:.1f}% dos eventos')

# Bio Index
print(f'\n[INDICE DE BIOINCRUSTACAO (0-10)]')
bi = df['bio_index_0_10']
print(f'   Media:    {bi.mean():.1f}')
print(f'   Mediana:  {bi.median():.1f}')
print(f'   Baixo (0-3):  {100*(bi <= 3).mean():.1f}%')
print(f'   Medio (4-6):  {100*((bi > 3) & (bi <= 6)).mean():.1f}%')
print(f'   Alto (7-10):  {100*(bi > 6).mean():.1f}%')

# Impacto financeiro e ambiental
print(f'\n[IMPACTO FINANCEIRO E AMBIENTAL]')
total_add_fuel = df['additional_fuel_tons'].sum()
total_add_cost = df['additional_cost_usd'].sum()
total_add_co2 = df['additional_co2_tons'].sum()
print(f'   Combustivel extra total: {total_add_fuel:,.0f} toneladas')
print(f'   Custo extra total:       USD {total_add_cost:,.0f}')
print(f'   CO2 extra total:         {total_add_co2:,.0f} toneladas')

# Separar positivo e negativo
pos_mask = df['additional_cost_usd'] > 0
neg_mask = df['additional_cost_usd'] < 0
print(f'\n   Custo EXTRA (biofouling):    USD {df.loc[pos_mask, "additional_cost_usd"].sum():>12,.0f}')
print(f'   "Economia" (ER negativo):   USD {df.loc[neg_mask, "additional_cost_usd"].sum():>12,.0f}')

# Top 5 navios com maior custo adicional
print(f'\n[TOP 5 NAVIOS - MAIOR CUSTO ADICIONAL]')
top_ships = df.groupby('shipName')['additional_cost_usd'].sum().sort_values(ascending=False).head(5)
for ship, cost in top_ships.items():
    print(f'   {ship:25}: USD {cost:>12,.0f}')

# Top 5 navios com pior ER medio
print(f'\n[TOP 5 NAVIOS - PIOR ER MEDIO (mais incrustados)]')
worst_er = df.groupby('shipName')['target_excess_ratio'].mean().sort_values(ascending=False).head(5)
for ship, er_val in worst_er.items():
    print(f'   {ship:25}: ER = {er_val*100:>+6.1f}%')

# Top 5 navios com melhor ER medio
print(f'\n[TOP 5 NAVIOS - MELHOR ER MEDIO (mais eficientes)]')
best_er = df.groupby('shipName')['target_excess_ratio'].mean().sort_values(ascending=True).head(5)
for ship, er_val in best_er.items():
    print(f'   {ship:25}: ER = {er_val*100:>+6.1f}%')

# Eventos criticos (Severa)
print(f'\n[EVENTOS CRITICOS (CLASSIFICACAO SEVERA)]')
severa = df[df['bio_class'] == 'Severa']
print(f'   Total de eventos severos: {len(severa):,}')
if len(severa) > 0:
    print(f'   ER medio em eventos severos: {severa["target_excess_ratio"].mean()*100:.1f}%')
    print(f'   Custo total de eventos severos: USD {severa["additional_cost_usd"].sum():,.0f}')
    severa_by_ship = severa.groupby('shipName').size().sort_values(ascending=False).head(5)
    print(f'   Navios com mais eventos severos:')
    for ship, count in severa_by_ship.items():
        print(f'      {ship}: {count} eventos')

print('\n' + '='*70)
