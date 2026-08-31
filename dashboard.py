import streamlit as st
import pandas as pd
import plotly.express as px
import os
import shutil
import re
from datetime import datetime

st.set_page_config(page_title="Статистика операторов", layout="wide")
st.title("📊 Статистика операторов")

# ===== ПУТИ =====
TICKETS_PATH = "data/tickets_data.csv"
CALLS_PATH = "data/calls_data.csv"
CSAT_PATH = "data/csat_data.csv"
HISTORY_DIR = "data/history"
HISTORY_TICKETS = f"{HISTORY_DIR}/history_tickets.csv"
HISTORY_CALLS = f"{HISTORY_DIR}/history_calls.csv"

# ===== ФУНКЦИИ =====
def load_any_file(filepath):
    """Загружает CSV или XLSX файл"""
    if not os.path.exists(filepath):
        return None
    
    # Если файл .xlsx — читаем через pandas
    if filepath.lower().endswith('.xlsx'):
        try:
            df = pd.read_excel(filepath, engine='openpyxl')
            return df
        except Exception as e:
            st.sidebar.error(f"Ошибка чтения XLSX: {e}")
            return None
    
    # Если файл .csv — пробуем разные разделители
    for sep in [';', ',', '\t']:
        for enc in ['utf-8-sig', 'utf-8', 'cp1251']:
            try:
                df = pd.read_csv(filepath, encoding=enc, delimiter=sep)
                if len(df.columns) > 1:
                    return df
            except:
                continue
    return None

def find_col(df, keywords):
    for col in df.columns:
        col_lower = col.lower().strip()
        for kw in keywords:
            if kw.lower() in col_lower:
                return col
    return None

def time_to_seconds(t):
    if isinstance(t, str) and ':' in t:
        parts = t.split(':')
        try:
            if len(parts) == 3:
                return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0])*60 + int(parts[1])
        except:
            pass
    return None

def get_last_name_simple(full_name):
    if not isinstance(full_name, str):
        return None
    name_clean = re.sub(r'\([^)]*\)', '', full_name).strip()
    parts = name_clean.split()
    if not parts:
        return None
    for part in reversed(parts):
        if part.endswith(('а', 'я', 'ов', 'ев', 'ин', 'ын', 'ский', 'цкая', 'цкий')):
            return part
    return parts[-1] if parts else None

def parse_csat_date(date_str):
    if not isinstance(date_str, str):
        return None
    date_part = re.sub(r'\s+в\s+\d{2}:\d{2}', '', date_str)
    months = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
    }
    try:
        parts = date_part.strip().split()
        if len(parts) == 3:
            day = int(parts[0])
            month = months.get(parts[1].lower(), 1)
            year = int(parts[2])
            return f"{year}-{month:02d}-{day:02d}"
    except:
        pass
    return None

def save_to_history(df, history_path, table_name):
    if df is None or len(df) == 0:
        return
    df = df.copy()
    
    # ПЕРЕИМЕНОВЫВАЕМ СТАРУЮ КОЛОНКУ "Дата", ЧТОБЫ НЕ КОНФЛИКТОВАТЬ
    if "Дата" in df.columns:
        df.rename(columns={"Дата": "Дата_загрузки"}, inplace=True)
    
    date_col = find_col(df, ["start_work_time", "start work time", "дата начала", "дата", "day", "date"])
    if date_col is not None:
        try:
            # УБИРАЕМ UTC, чтобы дата не смещалась
            df["Дата"] = pd.to_datetime(df[date_col], format='mixed')
            # Извлекаем только дату без времени
            df["Дата"] = df["Дата"].dt.date.astype(str)
        except Exception as e:
            df["Дата"] = datetime.now().date().strftime("%Y-%m-%d")
    else:
        df["Дата"] = datetime.now().date().strftime("%Y-%m-%d")
    
    # Удаляем дублирующиеся колонки
    df = df.loc[:, ~df.columns.duplicated()]
    
    if os.path.exists(history_path):
        df_old = load_any_file(history_path)
        if df_old is not None:
            df_combined = pd.concat([df_old, df], ignore_index=True)
            df_combined = df_combined.drop_duplicates()
        else:
            df_combined = df
    else:
        df_combined = df
    os.makedirs(HISTORY_DIR, exist_ok=True)
    df_combined.to_csv(history_path, index=False, encoding='utf-8-sig')
    return df_combined

def get_history_filter(df, key_suffix):
    if df is None or len(df) == 0:
        return df
    if "Дата" not in df.columns:
        return df
    try:
        df["Дата"] = pd.to_datetime(df["Дата"], format='mixed').dt.date
    except:
        try:
            df["Дата"] = pd.to_datetime(df["Дата"]).dt.date
        except:
            return df
    st.sidebar.subheader("📅 Фильтр по дате")
    col1, col2 = st.sidebar.columns(2)
    min_date = df["Дата"].min()
    max_date = df["Дата"].max()
    with col1:
        date_from = st.date_input("С", value=min_date, min_value=min_date, max_value=max_date, key=f"date_from_{key_suffix}")
    with col2:
        date_to = st.date_input("По", value=max_date, min_value=min_date, max_value=max_date, key=f"date_to_{key_suffix}")
    return df[(df["Дата"] >= date_from) & (df["Дата"] <= date_to)]

# ============================================================
# ЗАГРУЗКА CSAT
# ============================================================
def load_csat_data():
    if not os.path.exists(CSAT_PATH):
        return None
    df = load_any_file(CSAT_PATH)
    if df is None or len(df) == 0:
        return None
    csat_col = None
    date_col = None
    for col in df.columns:
        col_lower = col.lower()
        if "кто допустил ошибку" in col_lower:
            csat_col = col
        if "обновлено" in col_lower or "дата" in col_lower:
            date_col = col
    if csat_col is None:
        return None
    errors_list = []
    for idx, row in df.iterrows():
        val = row[csat_col]
        if pd.isna(val):
            continue
        if date_col is not None:
            task_date = parse_csat_date(str(row[date_col]))
            if task_date is None:
                task_date = datetime.now().date().strftime("%Y-%m-%d")
        else:
            task_date = datetime.now().date().strftime("%Y-%m-%d")
        employees = [x.strip() for x in str(val).split(',') if x.strip()]
        for emp in employees:
            full_name = re.sub(r'\([^)]*\)', '', emp).strip()
            errors_list.append({
                "Сотрудник": full_name,
                "Фамилия": get_last_name_simple(emp),
                "Дата": task_date
            })
    if not errors_list:
        return None
    df_csat = pd.DataFrame(errors_list)
    return df_csat

# ============================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================
df_history_tickets = load_any_file(HISTORY_TICKETS)
df_history_calls = load_any_file(HISTORY_CALLS)
df_csat_raw = load_csat_data()

df_new_tickets = load_any_file(TICKETS_PATH)
df_new_calls = load_any_file(CALLS_PATH)

# ===== КНОПКИ ЗАГРУЗКИ =====
st.sidebar.header("📥 Загрузка данных")

if df_new_tickets is not None:
    st.sidebar.success(f"📋 Найден tickets_data.csv/xlsx ({len(df_new_tickets)} записей)")
    if st.sidebar.button("📥 Добавить тикеты в историю"):
        save_to_history(df_new_tickets, HISTORY_TICKETS, "Тикеты")
        os.makedirs("data/archive", exist_ok=True)
        ext = os.path.splitext(TICKETS_PATH)[1]
        shutil.move(TICKETS_PATH, f"data/archive/tickets_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        st.rerun()
else:
    st.sidebar.warning("📁 Нет нового файла tickets_data.csv или tickets_data.xlsx")

if df_new_calls is not None:
    st.sidebar.success(f"📞 Найден calls_data.csv/xlsx ({len(df_new_calls)} записей)")
    if st.sidebar.button("📥 Добавить звонки в историю"):
        save_to_history(df_new_calls, HISTORY_CALLS, "Звонки")
        os.makedirs("data/archive", exist_ok=True)
        ext = os.path.splitext(CALLS_PATH)[1]
        shutil.move(CALLS_PATH, f"data/archive/calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        st.rerun()
else:
    st.sidebar.warning("📁 Нет нового файла calls_data.csv или calls_data.xlsx")

st.sidebar.divider()
st.sidebar.subheader("📊 История")

if df_history_tickets is not None:
    st.sidebar.info(f"📋 Тикеты: {len(df_history_tickets)} записей")
if df_history_calls is not None:
    st.sidebar.info(f"📞 Звонки: {len(df_history_calls)} записей")
if df_csat_raw is not None:
    st.sidebar.success(f"✅ CSAT загружен: {len(df_csat_raw)} записей")

# ===== ВКЛАДКИ =====
tab1, tab2, tab3 = st.tabs(["📋 Тикеты", "📞 Звонки", "📊 CSAT"])

# ============================================================
# ТИКЕТЫ
# ============================================================
with tab1:
    if df_history_tickets is None or len(df_history_tickets) == 0:
        st.warning("📁 Нет истории по тикетам. Загрузите файл через боковую панель.")
    else:
        df = df_history_tickets.copy()
        df_filtered = get_history_filter(df, "tickets")
        
        if len(df_filtered) == 0:
            st.warning("Нет данных за выбранный период")
        else:
            st.subheader(f"📋 Тикеты — {len(df_filtered)} записей за период")
            
            # ---- ПОИСК ПО СОТРУДНИКУ ----
            search_term = st.text_input(
                "🔍 Поиск по сотруднику",
                placeholder="Введите фамилию или часть ФИО",
                key="tickets_search"
            )
            
            if search_term:
                search_lower = search_term.lower().strip()
                df_filtered = df_filtered[
                    df_filtered["Сотрудник"].str.lower().str.contains(search_lower, na=False)
                ]
                st.caption(f"🔍 Найдено: {len(df_filtered)} записей")
            
            emp = find_col(df_filtered, ["сотрудник"])
            tickets_col = find_col(df_filtered, ["закрытых", "тикетов", "продуктивной"])
            transfer_col = find_col(df_filtered, ["переведенных"])
            sl_col = find_col(df_filtered, ["sl решения"])
            work_time_col = find_col(df_filtered, ["среднее время работы"])
            crm_col = find_col(df_filtered, ["рабочее время crm"])
            break_col = find_col(df_filtered, ["перерыв crm"])
            prod_transfer_col = find_col(df_filtered, ["переводы/час"])
            prod_closed_col = find_col(df_filtered, ["закрытые тикеты/час"])
            prod_all_col = find_col(df_filtered, ["все тикеты/час"])
            
            rename = {}
            if emp: rename[emp] = "Сотрудник"
            if tickets_col: rename[tickets_col] = "Тикеты"
            if transfer_col: rename[transfer_col] = "Переведено"
            if sl_col: rename[sl_col] = "SL решения"
            if work_time_col: rename[work_time_col] = "Среднее время работы"
            if crm_col: rename[crm_col] = "Рабочее время CRM"
            if break_col: rename[break_col] = "Перерыв CRM"
            if prod_transfer_col: rename[prod_transfer_col] = "Производительность (переводы/час)"
            if prod_closed_col: rename[prod_closed_col] = "Производительность (закрытые тикеты/час)"
            if prod_all_col: rename[prod_all_col] = "Производительность (все тикеты/час)"
            
            df_filtered.rename(columns=rename, inplace=True)
            
            if "Тикеты" in df_filtered.columns:
                df_filtered["Тикеты"] = pd.to_numeric(df_filtered["Тикеты"], errors='coerce').fillna(0).astype(int)
            
            for col in ["Производительность (переводы/час)", "Производительность (закрытые тикеты/час)", "Производительность (все тикеты/час)"]:
                if col in df_filtered.columns:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0).round(2)
            
            if "SL решения" in df_filtered.columns:
                df_filtered["SL решения"] = df_filtered["SL решения"].apply(lambda x: f"{float(x)*100:.0f}%" if pd.notna(x) and x != '' else "0%")
            
            needed_cols = ["Сотрудник", "Тикеты", "Переведено", "SL решения", 
                           "Среднее время работы", "Рабочее время CRM", "Перерыв CRM",
                           "Производительность (переводы/час)", 
                           "Производительность (закрытые тикеты/час)", 
                           "Производительность (все тикеты/час)", "Дата"]
            
            existing_cols = [col for col in needed_cols if col in df_filtered.columns]
            df_filtered = df_filtered[existing_cols]
            
            group_cols = ["Тикеты", "Переведено"]
            group_cols = [col for col in group_cols if col in df_filtered.columns]
            
            df_grouped = df_filtered.groupby("Сотрудник", as_index=False)[group_cols].sum()
            
            for col in ["Производительность (переводы/час)", "Производительность (закрытые тикеты/час)", "Производительность (все тикеты/час)"]:
                if col in df_filtered.columns:
                    df_grouped[col] = df_filtered.groupby("Сотрудник")[col].mean().round(2).values
            
            for col in ["Среднее время работы", "Рабочее время CRM", "Перерыв CRM", "SL решения"]:
                if col in df_filtered.columns:
                    df_grouped[col] = df_filtered.groupby("Сотрудник")[col].first().values
                else:
                    df_grouped[col] = "—"
            
            df_grouped["Дней"] = df_filtered.groupby("Сотрудник")["Дата"].nunique().values
            
            # ---- ПОДСТАВЛЯЕМ CSAT ----
            if df_csat_raw is not None:
                csat_counts = df_csat_raw.groupby("Фамилия").size().reset_index(name="CSAT")
                df_grouped["Фамилия"] = df_grouped["Сотрудник"].apply(get_last_name_simple)
                df_grouped = pd.merge(df_grouped, csat_counts, on="Фамилия", how="left")
                df_grouped["CSAT"] = df_grouped["CSAT"].fillna(0).astype(int)
                df_grouped.drop(columns=["Фамилия"], inplace=True, errors='ignore')
            else:
                df_grouped["CSAT"] = 0
            
            # ---- ИТОГОВАЯ СТРОКА ----
            total_row = {}
            total_row["Сотрудник"] = "ИТОГО ЗА ПЕРИОД"
            total_row["Тикеты"] = df_grouped["Тикеты"].sum() if "Тикеты" in df_grouped.columns else 0
            total_row["Переведено"] = df_grouped["Переведено"].sum() if "Переведено" in df_grouped.columns else 0
            total_row["CSAT"] = df_grouped["CSAT"].mean() if "CSAT" in df_grouped.columns else 0
            
            for col in ["Производительность (переводы/час)", "Производительность (закрытые тикеты/час)", "Производительность (все тикеты/час)"]:
                if col in df_grouped.columns:
                    total_row[col] = df_grouped[col].mean()
                else:
                    total_row[col] = 0
            
            total_row["Дней"] = df_filtered["Дата"].nunique()
            for col in ["Среднее время работы", "Рабочее время CRM", "Перерыв CRM", "SL решения"]:
                total_row[col] = "—"
            
            df_total = pd.DataFrame([total_row])
            df_display = pd.concat([df_total, df_grouped], ignore_index=True)
            
            # ---- KPI ----
            st.subheader("🎯 Общая статистика за период")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("📊 Всего тикетов", f"{total_row.get('Тикеты', 0):,}")
            with c2:
                st.metric("📈 Средняя производительность (все)", f"{total_row.get('Производительность (все тикеты/час)', 0):.2f}")
            with c3:
                st.metric("📈 Средняя производительность (закрытые)", f"{total_row.get('Производительность (закрытые тикеты/час)', 0):.2f}")
            with c4:
                if len(df_grouped) > 0 and "Тикеты" in df_grouped.columns:
                    best = df_grouped.loc[df_grouped["Тикеты"].idxmax(), "Сотрудник"]
                    st.metric("🏆 Лучший", best)
                else:
                    st.metric("🏆 Лучший", "—")
            
            # ---- ГРАФИК ----
            if "Сотрудник" in df_grouped.columns and "Тикеты" in df_grouped.columns:
                st.subheader("📊 Тикеты по сотрудникам за период")
                emp_sorted = df_grouped.sort_values("Тикеты", ascending=False)
                fig = px.bar(emp_sorted, x="Сотрудник", y="Тикеты", text="Тикеты")
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            # ---- ТАБЛИЦА С УСЛОВНЫМ ФОРМАТИРОВАНИЕМ ----
            st.subheader("📋 Таблица с подсветкой")
            
            def highlight_tickets(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                for i, row in df.iterrows():
                    if row.get("Сотрудник") == "ИТОГО ЗА ПЕРИОД":
                        for col in df.columns:
                            styles.iloc[i, df.columns.get_loc(col)] = 'background-color: #f0f0f0; font-weight: bold'
                        continue
                
                if "CSAT" in df.columns:
                    for i, val in enumerate(df["CSAT"]):
                        try:
                            v = float(val)
                            if v > 3:
                                styles.iloc[i, df.columns.get_loc("CSAT")] = 'background-color: #ffcccc'
                            elif v > 1:
                                styles.iloc[i, df.columns.get_loc("CSAT")] = 'background-color: #ffff99'
                            elif v == 0:
                                styles.iloc[i, df.columns.get_loc("CSAT")] = 'background-color: #ccffcc'
                        except:
                            pass
                
                if "Производительность (переводы/час)" in df.columns:
                    for i, val in enumerate(df["Производительность (переводы/час)"]):
                        try:
                            v = float(val)
                            if v < 3:
                                styles.iloc[i, df.columns.get_loc("Производительность (переводы/час)")] = 'background-color: #ffcccc'
                            elif v < 5:
                                styles.iloc[i, df.columns.get_loc("Производительность (переводы/час)")] = 'background-color: #ffff99'
                        except:
                            pass
                
                if "Производительность (закрытые тикеты/час)" in df.columns:
                    df_rating = df[df["Сотрудник"] != "ИТОГО ЗА ПЕРИОД"]
                    if len(df_rating) > 0:
                        max_val = df_rating["Производительность (закрытые тикеты/час)"].max()
                        min_val = df_rating["Производительность (закрытые тикеты/час)"].min()
                        if max_val > min_val:
                            for i, val in enumerate(df["Производительность (закрытые тикеты/час)"]):
                                try:
                                    v = float(val)
                                    if v == max_val:
                                        styles.iloc[i, df.columns.get_loc("Производительность (закрытые тикеты/час)")] = 'background-color: #ccffcc'
                                    elif v == min_val:
                                        styles.iloc[i, df.columns.get_loc("Производительность (закрытые тикеты/час)")] = 'background-color: #ffcccc'
                                except:
                                    pass
                
                if "Производительность (все тикеты/час)" in df.columns:
                    df_rating = df[df["Сотрудник"] != "ИТОГО ЗА ПЕРИОД"]
                    if len(df_rating) > 0:
                        max_val = df_rating["Производительность (все тикеты/час)"].max()
                        min_val = df_rating["Производительность (все тикеты/час)"].min()
                        if max_val > min_val:
                            for i, val in enumerate(df["Производительность (все тикеты/час)"]):
                                try:
                                    v = float(val)
                                    if v == max_val:
                                        styles.iloc[i, df.columns.get_loc("Производительность (все тикеты/час)")] = 'background-color: #ccffcc'
                                    elif v == min_val:
                                        styles.iloc[i, df.columns.get_loc("Производительность (все тикеты/час)")] = 'background-color: #ffcccc'
                                except:
                                    pass
                
                if "Среднее время работы" in df.columns:
                    df_rating = df[df["Сотрудник"] != "ИТОГО ЗА ПЕРИОД"]
                    max_time = None
                    for val in df_rating["Среднее время работы"]:
                        sec = time_to_seconds(val)
                        if sec is not None and (max_time is None or sec > max_time):
                            max_time = sec
                    if max_time is not None:
                        for i, val in enumerate(df["Среднее время работы"]):
                            sec = time_to_seconds(val)
                            if sec is not None and sec == max_time:
                                styles.iloc[i, df.columns.get_loc("Среднее время работы")] = 'background-color: #ffff99'
                
                return styles
            
            st.dataframe(df_display.style.apply(highlight_tickets, axis=None), use_container_width=True)

# ============================================================
# ЗВОНКИ
# ============================================================
with tab2:
    if df_history_calls is None or len(df_history_calls) == 0:
        st.warning("📁 Нет истории по звонкам. Загрузите файл через боковую панель.")
    else:
        df = df_history_calls.copy()
        df_filtered = get_history_filter(df, "calls")
        
        if len(df_filtered) == 0:
            st.warning("Нет данных за выбранный период")
        else:
            st.subheader(f"📞 Звонки — {len(df_filtered)} записей за период")
            
            # ---- ПОИСК ПО СОТРУДНИКУ ----
            search_term = st.text_input(
                "🔍 Поиск по сотруднику",
                placeholder="Введите фамилию или часть ФИО",
                key="calls_search"
            )
            
            if search_term:
                search_lower = search_term.lower().strip()
                df_filtered = df_filtered[
                    df_filtered["Сотрудник"].str.lower().str.contains(search_lower, na=False)
                ]
                st.caption(f"🔍 Найдено: {len(df_filtered)} записей")
            
            emp = find_col(df_filtered, ["сотрудник", "оператор"])
            calls = find_col(df_filtered, ["обработанные", "звонки"])
            missed = find_col(df_filtered, ["неотвеченные"])
            time_resp = find_col(df_filtered, ["среднее время ответа", "время ответа"])
            time_proc = find_col(df_filtered, ["среднее время в обработке", "время обработки"])
            time_post = find_col(df_filtered, ["среднее время в постобработке", "постобработка"])
            work_vox = find_col(df_filtered, ["рабочее время vox"])
            prod_vox = find_col(df_filtered, ["производительность vox"])
            
            rename = {}
            if emp: rename[emp] = "Сотрудник"
            if calls: rename[calls] = "Обработанные звонки"
            if missed: rename[missed] = "Неотвеченные звонки"
            if time_resp: rename[time_resp] = "Среднее время ответа"
            if time_proc: rename[time_proc] = "Среднее время в обработке"
            if time_post: rename[time_post] = "Среднее время в постобработке"
            if work_vox: rename[work_vox] = "Рабочее время VOX"
            if prod_vox: rename[prod_vox] = "Производительность VOX"
            
            df_filtered.rename(columns=rename, inplace=True)
            
            keep_cols = ["Сотрудник", "Обработанные звонки", "Неотвеченные звонки",
                         "Среднее время ответа", "Среднее время в обработке",
                         "Среднее время в постобработке", "Рабочее время VOX",
                         "Производительность VOX", "Дата"]
            
            final_cols = [col for col in keep_cols if col in df_filtered.columns]
            df_filtered = df_filtered[final_cols]
            
            if "Обработанные звонки" in df_filtered.columns:
                df_filtered["Обработанные звонки"] = pd.to_numeric(df_filtered["Обработанные звонки"], errors='coerce').fillna(0).astype(int)
            if "Неотвеченные звонки" in df_filtered.columns:
                df_filtered["Неотвеченные звонки"] = pd.to_numeric(df_filtered["Неотвеченные звонки"], errors='coerce').fillna(0).astype(int)
            if "Производительность VOX" in df_filtered.columns:
                df_filtered["Производительность VOX"] = pd.to_numeric(df_filtered["Производительность VOX"], errors='coerce').fillna(0).round(2)
            
            for col in ["Среднее время ответа", "Среднее время в обработке", "Среднее время в постобработке"]:
                if col in df_filtered.columns:
                    df_filtered[col] = df_filtered[col].fillna("00:00:00")
            
            group_cols = ["Обработанные звонки", "Неотвеченные звонки"]
            group_cols = [col for col in group_cols if col in df_filtered.columns]
            
            df_grouped = df_filtered.groupby("Сотрудник", as_index=False)[group_cols].sum()
            
            if "Производительность VOX" in df_filtered.columns:
                df_grouped["Производительность VOX"] = df_filtered.groupby("Сотрудник")["Производительность VOX"].mean().round(2).values
            else:
                df_grouped["Производительность VOX"] = 0
            
            for col in ["Среднее время ответа", "Среднее время в обработке", "Среднее время в постобработке", "Рабочее время VOX"]:
                if col in df_filtered.columns:
                    df_grouped[col] = df_filtered.groupby("Сотрудник")[col].first().values
                else:
                    df_grouped[col] = "—"
            
            df_grouped["Дней"] = df_filtered.groupby("Сотрудник")["Дата"].nunique().values
            
            total_row = {}
            total_row["Сотрудник"] = "ИТОГО ЗА ПЕРИОД"
            total_row["Обработанные звонки"] = df_grouped["Обработанные звонки"].sum() if "Обработанные звонки" in df_grouped.columns else 0
            total_row["Неотвеченные звонки"] = df_grouped["Неотвеченные звонки"].sum() if "Неотвеченные звонки" in df_grouped.columns else 0
            total_row["Производительность VOX"] = df_grouped["Производительность VOX"].mean() if "Производительность VOX" in df_grouped.columns else 0
            total_row["Дней"] = df_filtered["Дата"].nunique()
            
            for col in ["Среднее время ответа", "Среднее время в обработке", "Среднее время в постобработке", "Рабочее время VOX"]:
                total_row[col] = "—"
            
            df_total = pd.DataFrame([total_row])
            df_display = pd.concat([df_total, df_grouped], ignore_index=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Обработанные", f"{total_row.get('Обработанные звонки', 0):,}")
            with c2:
                st.metric("Неотвеченные", f"{total_row.get('Неотвеченные звонки', 0):,}")
            with c3:
                if len(df_grouped) > 0 and "Обработанные звонки" in df_grouped.columns:
                    best = df_grouped.loc[df_grouped["Обработанные звонки"].idxmax(), "Сотрудник"]
                    st.metric("🏆 Лучший", best)
                else:
                    st.metric("🏆 Лучший", "—")
            
            if "Сотрудник" in df_grouped.columns and "Обработанные звонки" in df_grouped.columns:
                st.subheader("📊 Обработанные звонки по операторам")
                emp_sorted = df_grouped.sort_values("Обработанные звонки", ascending=False)
                fig = px.bar(emp_sorted, x="Сотрудник", y="Обработанные звонки", text="Обработанные звонки")
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📋 Таблица с подсветкой")
            
            def highlight_calls(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                for i, row in df.iterrows():
                    if row.get("Сотрудник") == "ИТОГО ЗА ПЕРИОД":
                        for col in df.columns:
                            styles.iloc[i, df.columns.get_loc(col)] = 'background-color: #f0f0f0; font-weight: bold'
                        continue
                
                if "Неотвеченные звонки" in df.columns:
                    for i, val in enumerate(df["Неотвеченные звонки"]):
                        try:
                            v = float(val)
                            if v > 5:
                                styles.iloc[i, df.columns.get_loc("Неотвеченные звонки")] = 'background-color: #ffcccc'
                            elif v > 1:
                                styles.iloc[i, df.columns.get_loc("Неотвеченные звонки")] = 'background-color: #ffff99'
                        except:
                            pass
                
                if "Среднее время ответа" in df.columns:
                    for i, val in enumerate(df["Среднее время ответа"]):
                        sec = time_to_seconds(val)
                        if sec is not None:
                            if sec > 7:
                                styles.iloc[i, df.columns.get_loc("Среднее время ответа")] = 'background-color: #ffff99'
                            else:
                                styles.iloc[i, df.columns.get_loc("Среднее время ответа")] = 'background-color: #ccffcc'
                
                if "Среднее время в обработке" in df.columns:
                    for i, val in enumerate(df["Среднее время в обработке"]):
                        sec = time_to_seconds(val)
                        if sec is not None and sec > 300:
                            styles.iloc[i, df.columns.get_loc("Среднее время в обработке")] = 'background-color: #ffff99'
                
                if "Среднее время в постобработке" in df.columns:
                    for i, val in enumerate(df["Среднее время в постобработке"]):
                        sec = time_to_seconds(val)
                        if sec is not None:
                            if sec > 120:
                                styles.iloc[i, df.columns.get_loc("Среднее время в постобработке")] = 'background-color: #ffff99'
                            else:
                                styles.iloc[i, df.columns.get_loc("Среднее время в постобработке")] = 'background-color: #ccffcc'
                
                if "Производительность VOX" in df.columns:
                    for i, val in enumerate(df["Производительность VOX"]):
                        try:
                            v = float(val)
                            if v < 4.2:
                                styles.iloc[i, df.columns.get_loc("Производительность VOX")] = 'background-color: #ffff99'
                            else:
                                styles.iloc[i, df.columns.get_loc("Производительность VOX")] = 'background-color: #ccffcc'
                        except:
                            pass
                
                return styles
            
            styled_df = df_display.style.apply(highlight_calls, axis=None)
            
            st.markdown("""
            <style>
            .stDataFrame {
                font-size: 14px !important;
            }
            .stDataFrame table {
                width: 100% !important;
            }
            .stDataFrame td, .stDataFrame th {
                padding: 8px 12px !important;
                white-space: nowrap !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(styled_df, use_container_width=True)

# ============================================================
# CSAT
# ============================================================
with tab3:
    if df_csat_raw is None or len(df_csat_raw) == 0:
        st.warning("📁 Нет данных CSAT. Положите файл csat_data.csv или csat_data.xlsx в папку data/")
    else:
        st.subheader("📊 Ошибки CSAT")
        
        st.sidebar.subheader("📅 Фильтр CSAT")
        
        df_csat_raw["Дата"] = pd.to_datetime(df_csat_raw["Дата"]).dt.date
        
        min_date = df_csat_raw["Дата"].min()
        max_date = df_csat_raw["Дата"].max()
        
        col1, col2 = st.columns(2)
        with col1:
            csat_date_from = st.date_input(
                "CSAT С",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key="csat_date_from"
            )
        with col2:
            csat_date_to = st.date_input(
                "CSAT По",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key="csat_date_to"
            )
        
        df_csat_filtered = df_csat_raw[
            (df_csat_raw["Дата"] >= csat_date_from) &
            (df_csat_raw["Дата"] <= csat_date_to)
        ]
        
        st.caption(f"📅 Период: {csat_date_from} — {csat_date_to}")
        st.caption(f"📊 Всего ошибок: {len(df_csat_filtered)}")
        
        st.subheader("🔍 Поиск по сотруднику")
        
        search_term = st.text_input(
            "Введите фамилию или часть ФИО",
            placeholder="Например: Коклемина или Елизавета",
            key="csat_search"
        )
        
        df_csat_search = df_csat_filtered.copy()
        if search_term:
            search_lower = search_term.lower().strip()
            df_csat_search = df_csat_search[
                df_csat_search["Сотрудник"].str.lower().str.contains(search_lower, na=False)
            ]
            st.caption(f"🔍 Найдено: {len(df_csat_search)} записей")
        
        st.subheader("📋 Ошибки по сотрудникам")
        
        csat_grouped = df_csat_search.groupby("Сотрудник").size().reset_index(name="Количество ошибок")
        csat_grouped = csat_grouped.sort_values("Количество ошибок", ascending=False)
        
        st.dataframe(csat_grouped, use_container_width=True, hide_index=True)
        
        st.subheader("📋 Детальный список ошибок")
        st.dataframe(
            df_csat_search[["Дата", "Сотрудник"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Дата": st.column_config.DateColumn("Дата"),
                "Сотрудник": st.column_config.TextColumn("Сотрудник")
            }
        )
        
        st.subheader("📈 Ошибки по дням")
        daily_csat = df_csat_search.groupby("Дата").size().reset_index(name="Количество")
        fig = px.line(daily_csat, x="Дата", y="Количество", markers=True,
                      title="Количество ошибок CSAT по дням")
        st.plotly_chart(fig, use_container_width=True)

st.caption("💡 Данные хранятся в папке data/history/")