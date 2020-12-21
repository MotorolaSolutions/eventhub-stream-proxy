#  Copyright 2020 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted
"""EventHub Stream Proxy for serving EventHub stream to multiple clients."""

import queue
from concurrent import futures

import grpc
import pydevd_pycharm
from absl import app
from absl import flags
from absl import logging
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2_grpc

from eventhub_stream_proxy import eventhub_stream_proxy_impl
from proto import event_pb2_grpc
from utils import port_picker

_EVENTHUB_DEFAULT_CONSUMER_GROUP = '$default'

FLAGS = flags.FLAGS

flags.DEFINE_integer(
    'port', port_picker.get_unused_port(),
    'Service port. If port is not specified then random free '
    'port is chosen.')
flags.DEFINE_string('event_hub_conn_str', None, 'EventHub connection string')
flags.DEFINE_string('event_hub_name', None, 'EventHub name')
flags.DEFINE_string('event_hub_consumer_group',
                    _EVENTHUB_DEFAULT_CONSUMER_GROUP,
                    'EventHub consumer group to attach to')

flags.DEFINE_integer('debug_port', None, 'Debug port')


def main(_):
    """Main code."""

    if FLAGS.debug_port:
        pydevd_pycharm.settrace('localhost', port=FLAGS.debug_port,
                                stdoutToServer=True)

    # Rationale when setting value 1024*30.
    # Avg size of an event is 250-300 bytes.
    # That gives pretty room and takes less than 30 MB memory.
    event_queue = queue.Queue(maxsize=1024 * 100)

    event_hub_capture = eventhub_stream_proxy_impl.EventHubCapture(
        event_hub_info={
            'event_hub_conn_str': FLAGS.event_hub_conn_str,
            'event_hub_name': FLAGS.event_hub_name,
            'event_hub_consumer_group': FLAGS.event_hub_consumer_group
        },
        event_queue=event_queue,
        event_queue_put_timeout_sec=30)
    event_hub_capture.start()
    logging.info('Started EventHub capture thread')

    event_subscription_servicer = eventhub_stream_proxy_impl.EventSubscriptionServicer(
    )
    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, grpc_server)

    client_streaming = eventhub_stream_proxy_impl.ClientStreamer(
        event_subscription_servicer,
        event_queue,
        event_queue_get_batch_threshold=25)
    client_streaming.start()
    logging.info('Started client streaming thread')

    event_pb2_grpc.add_EventSubscriptionServicer_to_server(
        event_subscription_servicer, grpc_server)
    grpc_server.add_insecure_port(f'[::]:{FLAGS.port}')
    grpc_server.start()
    logging.info(
        f'Started EventSubscriptionServicer gRPC server on port {FLAGS.port}')
    grpc_server.wait_for_termination()


if __name__ == '__main__':
    flags.mark_flag_as_required('event_hub_conn_str')
    flags.mark_flag_as_required('event_hub_name')
    app.run(main)
