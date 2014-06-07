"""Main command module that starts the different threads."""
import datetime
import json
import logging
import signal
import socket
import sys

from command import Command
from message_router import MessageRouter
from telemetry import Telemetry

# pylint: disable=superfluous-parens
# pylint: disable=global-statement


THREADS = []
SOCKET = None


def terminate(signal_number, stack_frame):
    """Terminates the program. Used when a signal is received."""
    print(
        'Received signal {signal_number}, quitting'.format(
            signal_number=signal_number
        )
    )
    if SOCKET is not None:
        SOCKET.close()
    for thread in THREADS:
        thread.kill()
        thread.join()
    sys.exit(0)


def main(listen_interface, listen_port, connect_host, connect_port, logger):
    """Runs everything."""
    global SOCKET
    try:
        SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        SOCKET.bind((listen_interface, listen_port))
        SOCKET.settimeout(1)
    except IOError as ioe:
        logger.critical('Unable to listen on port: {ioe}'.format(ioe=ioe))
        sys.exit(1)

    class DgramSocketWrapper(object):
        """Simple wrapper around a socket so that modules don't need to worry
        about host, port, timeouts, or other details.
        """
        def __init__(self, host, port):
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._host = host
            self._port = port

        def send(self, message, request_response=None):
            """Sends a message through the socket."""
            if request_response is None:
                request_response = False
            if isinstance(message, list):
                if request_response and 'requestResponse' not in message:
                    message['requestResponse'] = True
                message_str = json.dumps(message)
            else:
                # If somebody's already converted to a string, then
                # request_response won't do anything
                assert not request_response
                message_str = message

            self._socket.sendto(message_str, (self._host, self._port))

    telemetry = Telemetry(logger)
    dgram_socket_wrapper = DgramSocketWrapper(connect_host, connect_port)
    command = Command(telemetry, dgram_socket_wrapper, dgram_socket_wrapper, logger)

    message_type_to_service = {
        'command': command,
        'telemetry': telemetry,
    }

    message_router = MessageRouter(SOCKET, message_type_to_service, logger)

    message_router.start()
    command.start()
    logger.info('Started all threads')
    global THREADS
    THREADS = [message_router, command]

    # Use a fake timeout so that the main thread can still receive signals
    message_router.join(100000000000)
    # Once we get here, message_router has died and there's no point in
    # continuing because we're not receiving telemetry messages any more, so
    # close the socket and stop the command module
    SOCKET.close()
    command.stop()
    command.join(100000000000)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, terminate)

    logger = logging.getLogger(__name__)
    # Log everything; filtering will be handled by the handlers
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s %(message)s'
    )

    file_handler = None
    try:
        now = datetime.datetime.now()
        file_handler = logging.FileHandler(
            '/media/USB/sparkfun-{date}.log'.format(
                date=datetime.datetime.strftime(
                    now,
                    '%Y-%m-%d-%H-%M'
                )
            )
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        logging.warning('Could not create file log: ' + str(e))
        pass

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    logger.info('test')

    main('0.0.0.0', 8384, '127.1', 12345, logger)
