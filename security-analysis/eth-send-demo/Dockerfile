FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY modules/ modules/
COPY poison/ poison/

EXPOSE 5001

CMD ["gunicorn", "--workers", "1", "--threads", "16", "--timeout", "120", "--bind", "0.0.0.0:5001", "--chdir", "api", "dashboard_api:app"]
