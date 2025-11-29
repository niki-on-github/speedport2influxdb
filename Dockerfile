FROM python:3.12-slim

WORKDIR /app

RUN pip install requests influxdb-client

COPY speedport_status.py .

CMD ["python", "-u", "speedport_status.py"]
