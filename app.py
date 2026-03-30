import streamlit as st
import os
import pandas as pd
import asyncio
from app.scraper import scrape

st.set_page_config(page_title="Siemens Scraper")

st.title("🔍 Siemens Product Scraper")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    os.makedirs("data/input", exist_ok=True)

    file_path = os.path.join("data/input", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("✅ CSV uploaded")

    if st.button("Run Scraper"):
        st.info("🚀 Running...")

        with st.spinner("Scraping..."):
            asyncio.run(scrape(file_path))   # ✅ FIXED

        st.success("✅ Done!")

        output_file = "data/output/output.xlsx"

        if os.path.exists(output_file):
            df = pd.read_excel(output_file)
            st.dataframe(df)

            with open(output_file, "rb") as f: 
                st.download_button("Download Excel", f, "output.xlsx")
