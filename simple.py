import streamlit as st
import pandas as pd
import os

st.title("📊 Тест загрузки")

paths = [
    "data/tickets_data.csv",
    "C:/Users/Ирина/Desktop/my_dashboard/data/tickets_data.csv"
]

for path in paths:
    st.write(f"Проверяю: {path}")
    if os.path.exists(path):
        st.success(f"✅ Файл найден! Размер: {os.path.getsize(path)} байт")
        try:
            df = pd.read_csv(path, encoding='utf-8-sig', delimiter=';')
            st.write("Колонки:", list(df.columns))
            st.dataframe(df)
        except Exception as e:
            st.error(f"Ошибка чтения: {e}")
    else:
        st.error(f"❌ Файл не найден")