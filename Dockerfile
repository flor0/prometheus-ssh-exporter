FROM python:latest

WORKDIR /usr/app/src

COPY prometheus-ssh-exporter.py ./
COPY requirements.txt ./

RUN pip3 install -r requirements.txt


# Set this to the port you chose in the prometheus-ssh-exporter.py file
EXPOSE 9999

CMD ["python", "./prometheus-ssh-exporter.py"]