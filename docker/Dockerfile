FROM python:3.9-bullseye

# Install prerequisite requirements
RUN apt-get update && apt-get -y install libgmp-dev libmpfr-dev libmpc-dev python3-pip

# Install requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Copy in app code
RUN mkdir /app
WORKDIR /app
COPY run.py .
COPY app ./app
COPY app/data/manifest.json data/manifest.json

# Run on port 0.0.0.0:80
CMD python run.py runserver -a "0.0.0.0" -p 80
