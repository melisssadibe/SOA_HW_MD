FROM python:3.9

WORKDIR /app

COPY api-gateway/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api-gateway/ .
COPY proto/ .

CMD ["python", "app.py"]
