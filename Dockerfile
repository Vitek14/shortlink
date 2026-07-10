FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copying project
COPY . .

RUN python manage.py collectstatic --noinput

# we will be running on port 8000, so opening it
EXPOSE 8000

# Using gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
