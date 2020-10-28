# Django container
FROM python:3
WORKDIR /usr/src/app

# Assorted posts recommend setting PYTHONUNBUFFERED but I'm not 100% on the consequences
ENV PYTHONUNBUFFERED 1
ENV GOOGLE_APPLICATION_CREDENTIALS /usr/src/app/gac.json

# Install requirements.txt
COPY requirements.txt /usr/
RUN pip install --no-cache-dir -r /usr/requirements.txt

# Install app by copying files to container
COPY . /usr/src/app

CMD ["python", "/usr/src/app/main.py"]
