import pandas as pd

# Читаем файл
df = pd.read_csv("data/weekly_data.csv", encoding='utf-8-sig', delimiter=';')

# Ищем строку-маркер
marker_idx = None
for idx, row in df.iterrows():
    row_text = ' '.join(str(val) for val in row.values if pd.notna(val))
    if 'Очередь' in row_text and 'Оператор' in row_text:
        marker_idx = idx
        break

if marker_idx is not None:
    # Разделяем
    df_tickets = df.iloc[:marker_idx].copy()
    df_calls = df.iloc[marker_idx:].copy()
    
    # Сохраняем
    df_tickets.to_csv("data/tickets.csv", index=False, encoding='utf-8-sig', sep=';')
    df_calls.to_csv("data/calls.csv", index=False, encoding='utf-8-sig', sep=';')
    
    print("✅ Файлы разделены:")
    print(f"   Тикеты: {len(df_tickets)} строк")
    print(f"   Звонки: {len(df_calls)} строк")
else:
    print("❌ Маркер не найден")