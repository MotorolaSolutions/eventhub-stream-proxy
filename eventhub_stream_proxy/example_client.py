# The MIT License (MIT)

# Copyright (C) 2020-2021 Motorola Solutions, Inc
# All rights reserved

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Simple client for EventHub Stream Proxy."""

import time
from concurrent import futures

import google.protobuf.empty_pb2
import google.protobuf.timestamp_pb2
import grpc
import pydevd_pycharm
from absl import app
from absl import flags
from absl import logging

from proto import event_pb2
from proto import event_pb2_grpc
from utils import port_picker

FLAGS = flags.FLAGS
flags.DEFINE_string('eventhub_stream_proxy_address', None,
                    'EventHub Stream Proxy address <hostname>:<port>')
flags.mark_flag_as_required('eventhub_stream_proxy_address')

flags.DEFINE_integer('debug_port', None, 'Debug port')


class EventReceiverServicer(event_pb2_grpc.EventReceiverServicer):
    """Implements receiver service to process incoming events."""

    def __init__(self):
        self.ready_to_unsubscribe = False

    def ReceiveEvents(self, events_iter, _):
        # pylint: disable=invalid-name
        """Get incoming events.

        Arguments:
            events_iter {iter} -- events got from EventHub Stream Proxy server

        Returns:
            google.protobuf.empty_pb2.Empty()
        """
        for event in events_iter:
            if not event.control:
                logging.info('Got event: %s', event.content)
                self.ready_to_unsubscribe = True
            else:
                logging.info('Got control event')

        return google.protobuf.empty_pb2.Empty()


def main(_):
    """Main function."""

    if FLAGS.debug_port:
        pydevd_pycharm.settrace('localhost', port=FLAGS.debug_port,
                                stdoutToServer=True)

    event_subscription = None
    subscriber_info = None
    try:
        port = port_picker.get_unused_port()

        event_receiver_servicer = EventReceiverServicer()

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
        event_pb2_grpc.add_EventReceiverServicer_to_server(
            event_receiver_servicer, server)
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        logging.info('Started gRPC server on port %s', port)

        # Subscribe.
        channel = grpc.insecure_channel(FLAGS.eventhub_stream_proxy_address)
        event_subscription = event_pb2_grpc.EventSubscriptionStub(channel)

        subscriber_info = event_pb2.SubscriberInfo()
        subscriber_info.hostname = port_picker.get_host_name()
        subscriber_info.port = port

        event_subscription.Subscribe(subscriber_info)

        while not event_receiver_servicer.ready_to_unsubscribe:
            logging.info('Waiting for any event...')
            time.sleep(1)

        logging.info('Unsubscribing')
        event_subscription.Unsubscribe(subscriber_info)

    except Exception as ex:
        logging.fatal('Unexpected exception: %s', ex)
    finally:
        if event_subscription and subscriber_info:
            event_subscription.Unsubscribe(subscriber_info)


if __name__ == '__main__':
    app.run(main)
