FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ agent/
COPY mcp_server/ mcp_server/

RUN useradd -m -u 1000 user
USER user

EXPOSE 8501
CMD ["streamlit", "run", "agent/ui.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]