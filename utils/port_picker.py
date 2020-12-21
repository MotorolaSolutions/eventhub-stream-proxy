#  Copyright 2018-2020 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted
"""Port utitlities."""
import socket

from absl import app
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_bool('print_ip', False, 'Print local hosts ip')
flags.DEFINE_bool('print_port', True, 'Print unused port')


def get_unused_port():
    """Returns (int) unused port number.
  """
    socket_candidate = socket.socket()
    socket_candidate.bind(('', 0))
    result = socket_candidate.getsockname()[1]
    socket_candidate.close()
    return result


def get_host_name():
    """Returns (string) local host IP.
  """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(('111.111.111.111', 1))
    result = sock.getsockname()[0]
    sock.close()
    return result


def main(_):
    """Main function."""
    result = []
    if FLAGS.print_ip:
        result.append(get_host_name())
    if FLAGS.print_port:
        result.append(str(get_unused_port()))
    print(':'.join(result))


if __name__ == '__main__':
    app.run(main)
