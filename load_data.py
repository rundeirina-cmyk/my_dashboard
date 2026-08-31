import pandas as pd
import os
from datetime import datetime

NEW_DATA_PATH = "data/weekly_data.csv"
HISTORY_TICKETS_PATH = "data/history_tickets.csv"
HISTORY_CALLS_PATH = "data/history_calls.csv"

def load_csv_with_encoding(filepath):
    encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251', 'latin-1']
    for enc in encodings:
        try:
            return pd.read_csv(filepath, encoding=enc, delimiter=';')
        except:
            continue
    return None

def detect_table_type(df):
    cols = ' '.join(df.columns.astype(str))
    print(f"🔍 Поиск типа таблицы. Колонки: {cols[:200]}...")
    
    # Проверяем наличие ключевых колонок
    if 'Кол-во закрытых тикетов с продуктивной резолюцией' in cols or 'закрытых тикетов' in cols:
        return 'tickets'
    if 'Обработанные звонки' in cols or 'Неотвеченные звонки' in cols:
        return 'calls'
    if 'Оператор' in cols and 'Очередь' in cols:
        return 'calls'
    
    # Если есть "Сотрудник" и "CSAT" — это скорее всего тикеты
    if 'Сотрудник' in cols and 'CSAT' in cols:
        return 'tickets'
    
    # Если есть "Сотрудник" и "Обработанные" — это звонки
    if 'Сотрудник' in cols and ('Обработанные' in cols or 'звонки' in cols):
        return 'calls'
    
    return 'unknown'

def clean_tickets(df):
    if df is None or len(df) == 0:
        print("❌ DataFrame пустой")
        return None
    
    print(f"📋 Обработка тикетов. Колонки: {list(df.columns)}")
    
    # Удаляем дублирующиеся колонки
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Выводим реальные названия колонок для диагностики
    print("📋 Реальные названия колонок в файле:")
    for col in df.columns:
        print(f"   - '{col}'")
    
    # Нужные колонки для тикетов
    # Мы будем искать их по частичному совпадению
    column_mapping = {}
    
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'сотрудник' in col_lower:
            column_mapping[col] = 'Сотрудник'
        elif 'csat' in col_lower:
            column_mapping[col] = 'CSAT'
        elif 'закрытых' in col_lower and 'тикетов' in col_lower:
            column_mapping[col] = 'Кол-во закрытых тикетов с продуктивной резолюцией'
        elif 'переведенных' in col_lower and 'тикетов' in col_lower:
            column_mapping[col] = 'Кол-во переведенных тикетов'
        elif 'среднее время решения' in col_lower:
            column_mapping[col] = 'Среднее время решения операторов'
        elif 'среднее время работы' in col_lower:
            column_mapping[col] = 'Среднее время работы в тикете'
        elif 'рабочее время' in col_lower and 'crm' in col_lower:
            column_mapping[col] = 'Рабочее время CRM'
        elif 'перерыв' in col_lower and 'crm' in col_lower:
            column_mapping[col] = 'Перерыв CRM'
        elif 'производительность' in col_lower and 'переводы' in col_lower:
            column_mapping[col] = 'Производительность (переводы/час)'
        elif 'производительность' in col_lower and 'закрытые' in col_lower:
            column_mapping[col] = 'Производительность (закрытые тикеты/час)'
        elif 'производительность' in col_lower and 'все' in col_lower:
            column_mapping[col] = 'Производительность (все тикеты/час)'
    
    print(f"🔄 Найдено соответствий: {len(column_mapping)}")
    for old, new in column_mapping.items():
        print(f"   '{old}' → '{new}'")
    
    # Переименовываем
    df.rename(columns=column_mapping, inplace=True)
    
    # Если CSAT нет — добавляем
    if 'CSAT' not in df.columns:
        df['CSAT'] = 0
    
    # Список нужных колонок
    required_columns = [
        'Сотрудник',
        'CSAT',
        'Кол-во закрытых тикетов с продуктивной резолюцией',
        'Кол-во переведенных тикетов',
        'Среднее время решения операторов',
        'Среднее время работы в тикете',
        'Рабочее время CRM',
        'Перерыв CRM',
        'Производительность (переводы/час)',
        'Производительность (закрытые тикеты/час)',
        'Производительность (все тикеты/час)'
    ]
    
    # Оставляем только нужные колонки
    existing_columns = [col for col in required_columns if col in df.columns]
    if not existing_columns:
        print("❌ Не найдено ни одной нужной колонки!")
        print(f"   Доступно: {list(df.columns)}")
        # Возвращаем хотя бы то, что есть
        return df
    
    df = df[existing_columns]
    
    # Преобразуем числа
    for col in required_columns:
        if col in df.columns and col not in ['Сотрудник', 'CSAT', 'Среднее время решения операторов', 'Среднее время работы в тикете', 'Рабочее время CRM', 'Перерыв CRM']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    print(f"✅ После очистки: {len(df)} записей, колонки: {list(df.columns)}")
    return df

def clean_calls(df):
    if df is None or len(df) == 0:
        return None
    
    print(f"📞 Обработка звонков. Колонки: {list(df.columns)}")
    
    # Удаляем дублирующиеся колонки
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Сопоставление колонок
    column_mapping = {}
    
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'сотрудник' in col_lower:
            column_mapping[col] = 'Сотрудник'
        elif 'обработанные звонки' in col_lower or 'обработанные' in col_lower:
            column_mapping[col] = 'Обработанные звонки'
        elif 'неотвеченные звонки' in col_lower or 'неотвеченные' in col_lower:
            column_mapping[col] = 'Неотвеченные звонки'
        elif 'среднее время ответа' in col_lower:
            column_mapping[col] = 'Среднее время ответа'
        elif 'среднее время в обработке' in col_lower:
            column_mapping[col] = 'Среднее время в обработке'
        elif 'среднее время в постобработке' in col_lower:
            column_mapping[col] = 'Среднее время в постобработке'
        elif 'рабочее время vox' in col_lower:
            column_mapping[col] = 'Рабочее время VOX'
        elif 'производительность vox' in col_lower:
            column_mapping[col] = 'Производительность VOX'
    
    print(f"🔄 Найдено соответствий: {len(column_mapping)}")
    for old, new in column_mapping.items():
        print(f"   '{old}' → '{new}'")
    
    df.rename(columns=column_mapping, inplace=True)
    
    # Нужные колонки
    required_columns = [
        'Сотрудник',
        'Обработанные звонки',
        'Неотвеченные звонки',
        'Среднее время ответа',
        'Среднее время в обработке',
        'Среднее время в постобработке',
        'Рабочее время VOX',
        'Производительность VOX'
    ]
    
    existing_columns = [col for col in required_columns if col in df.columns]
    if not existing_columns:
        print("❌ Не найдено ни одной нужной колонки для звонков!")
        print(f"   Доступно: {list(df.columns)}")
        return df
    
    df = df[existing_columns]
    
    # Преобразуем числа
    for col in ['Обработанные звонки', 'Неотвеченные звонки', 'Производительность VOX']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    print(f"✅ После очистки: {len(df)} записей, колонки: {list(df.columns)}")
    return df

def save_history(df, path, table_name):
    if df is None or len(df) == 0:
        print(f"⚠️ Нет данных для сохранения ({table_name})")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    df["Дата загрузки"] = today
    
    # Удаляем дублирующиеся колонки
    df = df.loc[:, ~df.columns.duplicated()]
    
    df.to_csv(path, index=False, encoding='utf-8-sig', sep=';')
    print(f"✅ {table_name} сохранена. Всего записей: {len(df)}")
    print(f"   Колонки: {', '.join(df.columns)}")

def load_new_data():
    if not os.path.exists(NEW_DATA_PATH):
        print("❌ Нет нового файла weekly_data.csv")
        return
    
    df_raw = load_csv_with_encoding(NEW_DATA_PATH)
    if df_raw is None:
        print("❌ Не удалось прочитать файл")
        return
    
    table_type = detect_table_type(df_raw)
    print(f"📋 Определён тип: {table_type}")
    
    if table_type == 'tickets':
        df_clean = clean_tickets(df_raw)
        save_history(df_clean, HISTORY_TICKETS_PATH, "История тикетов")
    elif table_type == 'calls':
        df_clean = clean_calls(df_raw)
        save_history(df_clean, HISTORY_CALLS_PATH, "История звонков")
    else:
        print("❌ Не удалось определить тип таблицы")
        print(f"   Колонки: {', '.join(df_raw.columns)}")
        return
    
    os.makedirs("data/archive", exist_ok=True)
    archive_path = f"data/archive/weekly_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    os.rename(NEW_DATA_PATH, archive_path)
    print(f"📁 Архив: {archive_path}")

if __name__ == "__main__":
    load_new_data()