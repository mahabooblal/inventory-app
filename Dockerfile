FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV FLASK_APP=app
ENV FLASK_ENV=production
EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:create_app()"]
