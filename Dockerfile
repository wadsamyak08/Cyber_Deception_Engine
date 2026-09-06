FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 2222 8080 2121 2323 33060 5000
CMD ["python", "desktop_app.py"]
