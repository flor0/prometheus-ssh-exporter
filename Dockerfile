FROM python:latest

WORKDIR /usr/app/src

COPY prometheus-ssh-exporter.py ./
COPY requirements.txt ./

RUN pip3 install -r requirements.txt

# Set this to the port you want to expose
EXPOSE 9999

# Set the -p option to the port you exposed above, defaults to 9999
CMD ["python", "-u", "./prometheus-ssh-exporter.py","-p", "9999"]