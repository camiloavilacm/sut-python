FROM python@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home qa
COPY --chown=10001:10001 app.py ./
COPY --chown=10001:10001 db ./db
COPY --chown=10001:10001 contracts ./contracts
COPY --chown=10001:10001 frontend ./frontend
USER 10001
EXPOSE 8000
CMD ["sh", "-c", "python app.py && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile /dev/null --error-logfile - app:app"]
