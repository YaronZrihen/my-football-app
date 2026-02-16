import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# עיצוב בסיסי
st.markdown("<style>.stApp {direction: rtl; text-align: right;}</style>", unsafe_allow_html=True)

# חיבור (תחליף ללינק שלך)
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1oexl9m3FA1T8zWOkTOSUuhBjBm2c5nZVIRqfNjtLS0M/edit?gid=1767684040#gid=1767684040"

# טעינת נתונים
try:
    df = conn.read(spreadsheet=SHEET_URL, ttl="0")
    players = df.to_dict(orient='records')
except:
    players = []

st.title("📝 עדכון פרטים")

# בחירת שם
names = [p['name'] for p in players] if players else []
selected = st.selectbox("בחר שם:", ["---"] + names + ["🆕 שחקן חדש"])

if selected != "---":
    # יצירת טופס עם KEY מפורש
    with st.form(key="my_player_form"):
        st.write(f"מעדכן פרטים עבור: {selected}")
        
        # שדות הקלט
        new_year = st.number_input("שנת לידה:", 1950, 2026, 1995)
        new_pos = st.text_input("תפקיד (למשל: חלוץ, בלם):")
        
        # הכפתור שחייב להיות כאן!
        submit_button = st.form_submit_button(label="שמור נתונים")
        
        if submit_button:
            st.success("הכפתור נלחץ!")
            # כאן תבוא הלוגיקה של השמירה אחרי שנראה שזה עובד
