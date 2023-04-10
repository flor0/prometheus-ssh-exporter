import prometheus_client
import time
import argparse
import utmp

# These defaults can be overwritten by command line arguments
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 9999
FETCH_INTERVAL = 5


class Session:
    """ This class is used to create a Session object containing info on an SSH session, mainly for readability 
    Only the fields name, tty, from_, login are actually used for now """

    def __init__(self, name, tty, from_, login, idle, jcpu, pcpu, what):
        self.name = name # Username that is logged in
        self.tty = tty # Which tty is used
        self.from_ = from_ # remote IP address
        self.login = login # time of login
        self.idle = idle # unused
        self.jcpu = jcpu # unused
        self.pcpu = pcpu # unused
        self.what = what # unused

    def __str__(self):
        return "%s %s" % (self.name, self.from_)

    def __repr__(self):
        return "%s %s" % (self.name, self.from_)

    def __eq__(self, other):
        return self.login == other.login and self.tty == other.tty and self.from_ == other.from_

    def to_dict(self):
        # maybe this will be used later
        return {
            'name': self.name,
            'tty': self.tty,
            'from_': self.from_,
            'login': self.login,
            'idle': self.idle,
            'jcpu': self.jcpu,
            'pcpu': self.pcpu,
            'what': self.what
        }

    def to_list(self):
        return [self.name, self.tty, self.from_, self.login, self.idle, self.jcpu, self.pcpu, self.what]


def contains_user_list(user, other_user_list):
    for other_user in other_user_list:
        if are_equal(user, other_user):
            return True
    return False


def are_equal(user_list, other_user_list):
    """ Two SSh sessions are equal if their name, tty, remote IP and login time are equal
    The other fields change over time hence they are not used for comparison """
    assert len(user_list) == len(other_user_list)
    for i in range(4):
        if user_list[i] != other_user_list[i]:
            return False
    return True


def get_utmp_data():
    """
    Returns a list of User Objects
    The function uses the utmp library. The utmp file contains information about currently logged in users
    """
    users = []
    with open('/var/run/utmp', 'rb') as f:
        buffer = f.read()
        for record in utmp.read(buffer):
            if record.type == utmp.UTmpRecordType.user_process:
                users.append(Session(record.user, record.line, record.host, record.sec, 0, 0, 0, 0))
    return users



def parse_arguments():

    global FETCH_INTERVAL, SERVER_PORT, SERVER_HOST

    parser = argparse.ArgumentParser(
        prog='python prometheus-ssh-exporter.py',
        description='Prometheus exporter for info about SSH sessions')
    parser.add_argument('-H', '--host', type=str,
                        default='0.0.0.0', help='Hostname to bind to')
    parser.add_argument('-p', '--port', type=int, default=9999,
                        help='Port for the server to listen to')
    parser.add_argument('-i', '--interval', type=int, default=15,
                        help='Interval in seconds to fetch SSH sessions data')

    args = parser.parse_args()
    FETCH_INTERVAL = args.interval
    SERVER_PORT = args.port
    SERVER_HOST = args.host


if __name__ == '__main__':
    """
    This program exports the number of SSH sessions as a metric "ssh_num_sessions" for prometheus.
    It applies a label to each increment or decrement of that number, containing the remote IP address.
    That way we can filter by the remote IP in Grafana, getting the number of SSH sessions by IP address,
    or sum them up to get the total number of sessions.
    """

    parse_arguments()

    # Start up the server to expose the metrics.
    prometheus_client.start_http_server(SERVER_PORT)
    print("Started metrics server bound to {}:{}".format(SERVER_HOST, SERVER_PORT))
    num_sessions = []
    gauge_num_sessions = prometheus_client.Gauge(
        'ssh_num_sessions', 'Number of SSH sessions', ['remote_ip'])
    # data = get_w_data()
    data = get_utmp_data()
    list_data = [user.to_list() for user in data]

    # Initial metrics
    print("Connections at startup:")
    for i in range(len(list_data)):
        gauge_num_sessions.labels(remote_ip=list_data[i][2]).inc()
        print("Initial connection: {}".format(list_data[i]))

    # Generate some requests.
    print("Looking for SSH connection changes at interval {}".format(FETCH_INTERVAL))
    while True:

        list_old_data = list_data
        # data = get_w_data()
        data = get_utmp_data()
        list_data = [user.to_list() for user in data]
        num_sessions = len(data)

        for i in range(num_sessions):
            # Looking for newly found SSH sessions
            if not contains_user_list(list_data[i], list_old_data):
                print("Session connected: %s" % list_data[i])
                gauge_num_sessions.labels(remote_ip=list_data[i][2]).inc()

        for i in range(len(list_old_data)):
            # Looking for SSH sessions that no longer exist
            if not contains_user_list(list_old_data[i], list_data):
                print("Session disconnected: %s" % list_old_data[i])
                gauge_num_sessions.labels(remote_ip=list_old_data[i][2]).dec()

        time.sleep(FETCH_INTERVAL)
