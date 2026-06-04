@echo off
cd /d "%~dp0"
..\mergent_enrichment\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\mergent_enrichment\.venv\Scripts\python.exe -m streamlit run app.py --server.port=8507
pause
