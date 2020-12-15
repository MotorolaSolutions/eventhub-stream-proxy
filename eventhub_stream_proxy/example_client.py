#  Copyright 2020 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted
"""Simple client for EventHub Stream Proxy."""

from concurrent import futures
import time

from absl import logging
from absl import app
from absl import flags

import grpc
import google.protobuf.timestamp_pb2
import google.protobuf.empty_pb2

from utils import port_picker
from proto import event_pb2_grpc
from proto import event_pb2

FLAGS = flags.FLAGS
flags.DEFINE_string('eventhub_stream_proxy_address', None,
                    'EventHub Stream Proxy address <hostname>:<port>')
flags.mark_flag_as_required('eventhub_stream_proxy_address')


class EventReceiverServicer(event_pb2_grpc.EventReceiverServicer):
    """Implements receiver service to process incoming events."""

    def __init__(self):
        self.ready_to_unsubscribe = False

    def ReceiveEvents(self, events_iter, _):
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


def main(argv):
    """Main function."""
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

    except Exception as e:
        logging.fatal('Unexpected exception: %s', e)
    finally:
        if event_subscription and subscriber_info:
            event_subscription.Unsubscribe(subscriber_info)


if __name__ == '__main__':
    app.run(main)
