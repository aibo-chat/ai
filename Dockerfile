FROM python:3.10.7
WORKDIR /app

COPY requirements.txt ./
RUN pip3 install -r requirements.txt
RUN pip3 install playwright==1.39.0
RUN playwright install-deps
RUN playwright install chromium
COPY . .
WORKDIR /app/src
CMD ["gunicorn", "aichat_app:app", "-c", "./gunicorn.conf.py"]