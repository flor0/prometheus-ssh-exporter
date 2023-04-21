import prometheus_client
import time
import argparse
import utmp
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


# These defaults can be overwritten by command line arguments
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 9999
FETCH_INTERVAL = 15
WATCHFILE = '/var/run/utmp'


class FileOpenedHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and isinstance(event, FileModifiedEvent) and event.src_path == WATCHFILE:
            handle_sessions_changed()


class Session:
    """ This class is used to create a Session object containing info on an SSH session, mainly for readability 
    Only the fields name, tty, from_, login are actually used for now """

    def __init__(self, name : str, tty : str, from_ : str, login : str, idle=0, jcpu=0, pcpu=0, what=0):
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


def get_utmp_data() -> list[Session]:
    """
    Returns a list of User Objects
    The function uses the utmp library. The utmp file contains information about ALL currently logged in users,
    including local users (not SSH sessions). We filter out the local users by checking if the remote IP address
    is empty and set the hostname for the local sessions to "localhost".
    """
    users : list[Session] = []
    with open('/var/run/utmp', 'rb') as fd:
        buffer = fd.read()
        for record in utmp.read(buffer):
            if record.type == utmp.UTmpRecordType.user_process:
                if record.host != '':
                    users.append(Session(record.user, record.line, record.host, record.sec))
                else:
                    users.append(Session(record.user, record.line, 'localhost', record.sec))
    return users



def handle_sessions_changed() -> None:
    """ 
    This function fetches the current list of SSH sessions and compares it to the previous list of SSH sessions.
    If the number of sessions has changed, it increments or decrements the gauge_num_sessions metric
    and updates the session_data and num_sessions variables.
    """
    global session_data, num_sessions, gauge_num_sessions, old_session_data, old_num_sessions

    old_session_data = session_data
    old_num_sessions = len(old_session_data)

    session_data = get_utmp_data()
    num_sessions = len(session_data)

    for maybe_new_session in session_data:
        # Looking for newly found SSH sessions
        if not maybe_new_session in old_session_data:
            print("Session connected: %s" % maybe_new_session.from_)
            gauge_num_sessions.labels(remote_ip=maybe_new_session.from_).inc()

    for maybe_old_session in old_session_data:
        # Looking for SSH sessions that no longer exist
        if not maybe_old_session in session_data:
            print("Session disconnected: %s" % maybe_old_session.from_)
            gauge_num_sessions.labels(remote_ip=maybe_old_session.from_).dec()



def parse_arguments() -> None:
    global FETCH_INTERVAL, SERVER_PORT, SERVER_HOST, WATCHFILE

    parser = argparse.ArgumentParser(
        prog='python prometheus-ssh-exporter.py',
        description='Prometheus exporter for info about SSH sessions')
    parser.add_argument('-H', '--host', type=str,
                        default='0.0.0.0', help='Hostname to bind to')
    parser.add_argument('-p', '--port', type=int, default=9999,
                        help='Port for the server to listen to')
    parser.add_argument('-i', '--interval', type=int, default=15,
                        help='Interval in seconds to fetch SSH sessions data')
    parser.add_argument('-f', '--file', type=str, default='/var/run/utmp',
                        help='File that changes every time a new SSH session is opened or closed')

    args = parser.parse_args()
    FETCH_INTERVAL = args.interval
    SERVER_PORT = args.port
    SERVER_HOST = args.host
    WATCHFILE = args.file



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
    gauge_num_sessions = prometheus_client.Gauge(
        'ssh_num_sessions', 'Number of SSH sessions', ['remote_ip'])
    
    # session_data contains the current list of sessions
    session_data = get_utmp_data()
    num_sessions = len(session_data)
    
    # Initial metrics
    for session in session_data:
        gauge_num_sessions.labels(remote_ip=session.from_).inc()
        print("Initial connection: {}".format(session.from_))


    """
    Start the watchdog to monitor the WATCHDOG file for changes. 
    This is used to immediately look for changes in the SSH sessions when a new session is opened or closed
    to prevent missing any sessions that lasted less than the FETCH_INTERVAL.
    """
    event_handler = FileOpenedHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCHFILE, recursive=False)
    observer.start()

    # Generate some requests.
    print("Looking for SSH connection changes at interval {}".format(FETCH_INTERVAL))
    try:

        while True:
            # Keep looking for changes in the SSH sessions in case the watchdog missed something
            handle_sessions_changed()
            time.sleep(FETCH_INTERVAL)

    except KeyboardInterrupt:
        print("Manual interrupt...")
        observer.stop()
    observer.join()