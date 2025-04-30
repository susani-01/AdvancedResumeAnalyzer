
import streamlit as st
import pandas as pd
import pyodbc
import requests  

st.set_page_config(page_title="Resume Analyzer Dashboard", layout="wide")


AZURE_FUNCTION_URL = "https://resume-analyzer-new.azurewebsites.net/api/process_resume"

DB_CONFIG = {
    "server": "resume-sql-20750.database.windows.net",
    "database": "ResumeDB",
    "username": "sqladmin",
    "password": "YourPassword123!",
    "driver": "{ODBC Driver 17 for SQL Server}"
}

# --- New Upload Section ---
st.title("📄 Resume Analyzer Dashboard")

with st.expander("⬆️ Upload New Resume", expanded=True):
    uploaded_file = st.file_uploader("Drag & drop resume (PDF/DOCX)", type=["pdf", "docx"])
    if uploaded_file:
        with st.spinner("Analyzing resume..."):
            try:
                response = requests.post(AZURE_FUNCTION_URL, files={"file": uploaded_file}, timeout=60)
                if response.status_code == 200:
                    st.success("Analysis complete!")
                    st.json(response.json())
                    st.rerun()
                else:
                    st.error(f"Analysis failed: {response.text}")
            except Exception as e:
                st.error(f"Function call failed: {e}")
                

# --- Database Query ---
try:
    conn = pyodbc.connect(
        f'DRIVER={DB_CONFIG["driver"]};'
        f'SERVER={DB_CONFIG["server"]};'
        f'DATABASE={DB_CONFIG["database"]};'
        f'UID={DB_CONFIG["username"]};'
        f'PWD={DB_CONFIG["password"]}'
    )
    
    # DEBUG: Check table columns
    # st.write(pd.read_sql("SELECT TOP 1 * FROM dbo.ResumeAnalyses", conn))
    
    query = "SELECT * FROM dbo.ResumeAnalyses"  # ← Use correct column
    df = pd.read_sql(query, conn)
    conn.close()
    df.rename(columns={"Score": "match_score",
    "SkillsMatch": "skills",
    "FileName": "filename"
    }, inplace=True)

    # --- Visualizations ---
    st.subheader("📊 Historical Analysis Data")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Resumes Analyzed", len(df))
        if 'match_score' in df.columns:
            st.bar_chart(df.set_index('filename')['match_score'])
    with col2:
        if 'skills' in df.columns:
            top_skills = df['skills'].str.split(',').explode().str.strip().value_counts().head(5)
            st.dataframe(top_skills)
    st.dataframe(df)

except Exception as e:
    st.error(f"Database error: {e}")