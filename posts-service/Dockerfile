FROM python:3.10

WORKDIR /app

COPY posts-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY posts-service/ .
COPY proto/ .

CMD ["python", "server.py"]
