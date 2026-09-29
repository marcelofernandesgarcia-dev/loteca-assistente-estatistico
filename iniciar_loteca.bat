@echo off
rem Abre o app Loteca -- Assistente Estatistico com um duplo clique.
rem Ativa o .venv desta pasta e roda o Streamlit; fecha esta janela para
rem encerrar o app.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run app\main.py
pause
