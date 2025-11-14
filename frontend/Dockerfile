FROM python:3.13-slim

WORKDIR /frontend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["streamlit", "run", "dashboard.py", "--server.port=3000", "--server.address=0.0.0.0"]