#  Copyright 2020 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted
"""EventHub Stream Proxy for serving EventHub stream to multiple clients."""

import queue
import time
import uuid
from concurrent import futures
from datetime import datetime

import google.protobuf.empty_pb2
import grpc
from absl import logging
from azure.eventhub import EventHubConsumerClient

from proto import event_pb2
from proto import event_pb2_grpc
from utils import custom_collections

_EVENTHUB_DEFAULT_CONSUMER_GROUP = '$default'


class EventHubCapture:
    """Gets events from EventHub and puts them to the queue."""

    def __init__(self, event_hub_info, event_queue,
                 event_queue_put_timeout_sec):
        """Creates instance.

        Arguments:
            event_hub_info {dict} with keys 'event_hub_conn_str',
                    'event_hub_name', 'event_hub_consumer_group'
            event_queue_put_timeout_sec {int} -- timeout in sec before trying
        """

        self._receive_eventhub_client = EventHubConsumerClient.from_connection_string(
            event_hub_info['event_hub_conn_str'],
            consumer_group=_EVENTHUB_DEFAULT_CONSUMER_GROUP,
            eventhub_name=event_hub_info['event_hub_name'])

        self.event_hub_consumer_group = event_hub_info[
            'event_hub_consumer_group']
        self.event_queue = event_queue
        self.event_queue_put_timeout_sec = event_queue_put_timeout_sec

    def _on_event(self, _partition_context=None, event=None):
        event_data_str = event.body_as_str(encoding="UTF-8")
        event_data_sequence_number = event.sequence_number
        event_data_enqueued_time = event.enqueued_time
        logging.info(
            'Received event data: sequence_number=%s; '
            'enqueued_time=%s, data=%s', event_data_sequence_number,
            event_data_enqueued_time, event_data_str)

        event = event_pb2.Event()
        event.content = event_data_str
        event.timestamp.GetCurrentTime()
        event.id = str(uuid.uuid4())

        put_success = False
        while not put_success:
            try:
                self.event_queue.put(event,
                                     block=True,
                                     timeout=self.event_queue_put_timeout_sec)
                put_success = True
            except queue.Full:
                logging.info('Queue is full, retrying...')
                time.sleep(1)

        logging.info(
            'Queue put; there are now approximately %s events in queue',
            self.event_queue.qsize())

    def _run_receive_events_and_populate_queue_loop(self):
        try:
            with self._receive_eventhub_client:
                self._receive_eventhub_client.receive(
                    on_event=self._on_event, starting_position=datetime.now())
        except Exception as ex:
            logging.fatal(ex)

    def start(self):
        """Starts event capture thread and populate events to event_queue."""
        executor = futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(self._run_receive_events_and_populate_queue_loop)


class ClientStreamer:
    """Pushes message from events queue to subscribed clients."""

    _BATCH_QUEUE_GET_CHUNK_SIZE = 1000

    def __init__(self, event_subscription_servicer, event_queue,
                 event_queue_get_batch_threshold):
        """Creates instance.

        Arguments:
            event_subscription_servicer {EventSubscriptionServicer} --
                EventSubscription instance
            event_queue {queue.Queue} --
                reference to queue where from the events should be get
            event_queue_get_timeout_sec {int} --
                time in seconds to wait for new messages in queue
            event_queue_get_batch_threshold {int} --
                how many items must be in queue to start batch get

        """
        self.event_subscription_servicer = event_subscription_servicer
        self.event_queue = event_queue
        self.event_queue_get_batch_threshold = event_queue_get_batch_threshold

    def _stream_events_to_subscribers(self, events):
        event_receivers = self.event_subscription_servicer.event_receivers_dict
        dead_clients = []
        for client_address in list(event_receivers):
            for event in events:
                try:
                    event_receivers[client_address].ReceiveEvents(
                        iter([event]))
                    if event.control:
                        logging.info('Streamed control event to %s',
                                     client_address)
                    else:
                        logging.info('Streamed event with content %s to %s',
                                     event.content, client_address)
                except Exception as ex:
                    logging.warning('Nothing was streamed to %s, cause: %s',
                                    client_address, ex)
                    dead_clients.append(client_address)
                    break

            logging.info('Streamed %s event(s) to %s', len(events),
                         client_address)

        if len(event_receivers) == 0:
            logging.info('Nothing was streamed, no subscribers')

        for dead_client_address in dead_clients:
            self.event_subscription_servicer.unsubscribe_by_address(
                dead_client_address)

    def _stream(self):

        try:
            events_to_stream = []
            current_qsize = self.event_queue.qsize()

            while True:
                try:
                    event_from_queue = self.event_queue.get_nowait()
                    logging.info(
                        'Queue get; there are now approximately %s '
                        'events in queue', self.event_queue.qsize())
                    event_from_queue.control = False
                    events_to_stream.append(event_from_queue)

                    if current_qsize > self.event_queue_get_batch_threshold:
                        if len(events_to_stream
                               ) > self._BATCH_QUEUE_GET_CHUNK_SIZE - 1:
                            break
                    else:
                        break

                except queue.Empty:
                    break

            logging.info('Collected %s event(s) from queue',
                         len(events_to_stream))

            if len(events_to_stream) == 0:
                logging.info(
                    'Nothing was collected from queue, streaming control event')
                control_event = event_pb2.Event()
                control_event.control = True
                events_to_stream.append(control_event)
                time.sleep(1)

            self._stream_events_to_subscribers(events_to_stream)

        except Exception as ex:
            logging.fatal('Unexpected exception: %s', ex)

    def _run_stream_loop(self):
        while True:
            self._stream()

    def start(self):
        """Start client streaming thread."""
        executor = futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(self._run_stream_loop)


class EventSubscriptionServicer(event_pb2_grpc.EventSubscriptionServicer):
    """Implements subscription service."""

    def __init__(self):
        """Creates instance."""
        self.event_receivers_dict = custom_collections.ThreadSafeMap()

    def Subscribe(self, subscriber_info, _):
        # pylint: disable=invalid-name
        """Subscribe a new client.

        Arguments:
            subscriber_info {event_pb2.SubscriberInfo} -- client information

        Returns:
            google.protobuf.empty_pb2.Empty()
        """
        try:
            subscriber_address = f'{subscriber_info.hostname}:{subscriber_info.port}'

            channel = grpc.insecure_channel(subscriber_address)
            event_receiver = event_pb2_grpc.EventReceiverStub(channel)
            self.event_receivers_dict[subscriber_address] = event_receiver

            logging.info('Subscribed: %s. There are now %s clients subscribed',
                         subscriber_address, len(self.event_receivers_dict))
            return google.protobuf.empty_pb2.Empty()

        except Exception as ex:
            logging.fatal('Unexpected exception: %s', ex)

    def unsubscribe_by_address(self, subscriber_address):
        """Unsubscribe given client.

        Arguments:
            subscriber_address {string} -- client address host:port

        """

        if subscriber_address not in self.event_receivers_dict:
            logging.warning('Client %s not present on the subscribers list',
                            subscriber_address)
        else:
            self.event_receivers_dict.pop(subscriber_address)

        logging.info('Unsubscribed: %s. There are now %s clients subscribed',
                     subscriber_address, len(self.event_receivers_dict))

    def Unsubscribe(self, subscriber_info, _):
        # pylint: disable=invalid-name
        """Unsubscribe given client.

        Arguments:
            subscriber_info {event_pb2.SubscriberInfo} -- client information

        Returns:
            google.protobuf.empty_pb2.Empty()
        """

        subscriber_address = f'{subscriber_info.hostname}:{subscriber_info.port}'
        self.unsubscribe_by_address(subscriber_address)
        return google.protobuf.empty_pb2.Empty()
