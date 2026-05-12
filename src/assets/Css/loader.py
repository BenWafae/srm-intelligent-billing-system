import streamlit as st
import os

def load_css(*filenames):
    base_path = os.path.join(os.path.dirname(__file__))
    combined = ""
    for filename in filenames:
        path = os.path.join(base_path, filename)
        with open(path, "r", encoding="utf-8") as f:
            combined += f.read() + "\n"
    st.markdown(f"<style>{combined}</style>", unsafe_allow_html=True)
