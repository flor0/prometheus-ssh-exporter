# prometheus-ssh-exporter
A Prometheus exporter for monitoring SSH connections

This is a personal project I wrote because I couldn't find any prometheus exporters that I could monitor my SSH connections with.

## Installation
The recommended way is to use docker. The image is available on docker hub **flor0/prometheus-ssh-exporter**

### Docker

The container can be run using the docker command

`docker run -d -p <external port>:9999 -v /run/utmp:/run/utmp flor0/prometheus-ssh-exporter`

Simply change the \<external port\> to whatever port you want the server to listen to. The default listening port is 9999.

### Docker compose

Here is an example docker-compose file.
Change the \<external port\> to what you want the server to listen to.

```
version: "3"
services:
  prometheus-ssh-exporter:
    container_name: prometheus-ssh-exporter
    image: flor0/prometheus-ssh-exporter
    ports:
      - <external port>:9999
    volumes:
      - /run/utmp:/run/utmp
    restart: unless-stopped
```
Note: It is vital that /run/utmp is mapped in the docker container, otherwise the program can't get your session info!

### As a python script
Alternatively, you can simply run the prometheus-ssh-exporter.py file with python3.

The command line arguments are explained if you use `python3 ./prometheus-ssh-exporter.py -h`

Make sure you set the right external port using the -p or --port argument.

## Configuring Prometheus

To have prometheus collect our new metrics, we need to add our server to the prometheus.yml file.
To do that open the /etc/prometheus/prometheus.yml file in an editor and add the lines
```
- job_name: ssh
    static_configs:
      - targets: ['localhost:<external port>']
```
where you replace again the \<external port\> with the same port you used in the previous steps. Make sure it's indented correctly!

## Usage

You can go to your prometheus dashboard in the web browser and query ssh_num_sessions.
If everything is set up correctly you should get the metrics.

### Grafana

I have published a grafana dashboard that can be found at https://snapshots.raintank.io/dashboard/snapshot/fnZ63M865o3J0N0ne9lSKfezGe7ERYVN
or imported with the grafana-dashboard.json file.
![prometheus-grafana](https://user-images.githubusercontent.com/48520760/232910344-89fb6557-0160-4f83-a794-ebcca4df28df.png)


