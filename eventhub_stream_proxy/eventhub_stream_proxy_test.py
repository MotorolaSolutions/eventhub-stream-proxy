#  Copyright 2020 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted

import datetime
import queue
import mock

import eventhub_stream_proxy

from proto import event_pb2

from absl.testing import absltest
from absl.testing import flagsaver

from eventhub_stream_proxy import eventhub_stream_proxy_impl


class EventSubscriptionServicerTestCase(absltest.TestCase):

    def setUp(self):
        pass

    def test_event_subscription_servicer_subscribe_new_client(self):
        # Given.
        event_stream_proxy_servicer = eventhub_stream_proxy_impl.EventSubscriptionServicer(
        )
        subscriber_info = event_pb2.SubscriberInfo()
        subscriber_info.hostname = 'foobar'
        subscriber_info.port = 60000

        # When.
        event_stream_proxy_servicer.Subscribe(subscriber_info, None)

        # Then.
        subscriber_info_address = f'{subscriber_info.hostname}:{subscriber_info.port}'
        self.assertTrue(subscriber_info_address in
                        event_stream_proxy_servicer.event_receivers_dict)
        self.assertIsNotNone(event_stream_proxy_servicer.
                             event_receivers_dict[subscriber_info_address])

    def test_event_subscription_servicer_unsubscribe_existing_client(self):
        # Given.
        event_stream_proxy_servicer = eventhub_stream_proxy_impl.EventSubscriptionServicer(
        )
        subscriber_info = event_pb2.SubscriberInfo()
        subscriber_info.hostname = 'foobar'
        subscriber_info.port = 60000

        # When.
        event_stream_proxy_servicer.Subscribe(subscriber_info, None)
        event_stream_proxy_servicer.Unsubscribe(subscriber_info, None)

        # Then.
        subscriber_info_address = f'{subscriber_info.hostname}:{subscriber_info.port}'
        self.assertTrue(subscriber_info_address not in
                        event_stream_proxy_servicer.event_receivers_dict)


class EventHubCaptureTestCase(absltest.TestCase):

    def setUp(self):
        pass

    def test_event_hub_events_passed_to_queue(self):
        # Given.
        event_queue = queue.Queue(maxsize=10)
        event_hub_capture = eventhub_stream_proxy_impl.EventHubCapture(
            'Endpoint=sb://FQDN/;SharedAccessKeyName=KeyName;SharedAccessKey=KeyValue',
            'event_hub_name',
            'event_hub_consumer_group',
            event_queue,
            event_queue_put_timeout_sec=1)

        event_hub_capture._receive_eventhub_client = mock.MagicMock()

        eventhub_event = mock.MagicMock()
        eventhub_event.body_as_str = mock.MagicMock(
            return_value='Simple EventHub event')

        event_hub_capture._receive_eventhub_client.receive = mock.MagicMock(
            return_value=[eventhub_event])

        # When.
        event_hub_capture._on_event(partition_context=None,
                                    event=eventhub_event)

        # Then.
        event_from_queue = event_queue.get()
        self.assertEquals(event_from_queue.content, 'Simple EventHub event')


class ClientStreamerTestCase(absltest.TestCase):

    def setUp(self):
        pass

    def test_stream_event_when_no_receivers(self):
        # Given.
        event_stream_proxy_servicer = mock.MagicMock()
        event_stream_proxy_servicer.event_subscription_servicer.event_receivers_dict = {}
        event_queue = queue.Queue(maxsize=10)
        client_streamer = eventhub_stream_proxy_impl.ClientStreamer(
            event_stream_proxy_servicer,
            event_queue,
            event_queue_get_batch_threshold=10)

        event = event_pb2.Event()
        event.control = False
        event.id = 'id-123'
        event.content = 'example content'
        event.timestamp.GetCurrentTime()
        event_queue.put(event)

        # When.
        client_streamer._stream()

        # Then.
        # no exception

    def test_stream_events(self):
        # Given.
        event_receiver = mock.MagicMock()
        event_receiver_address = 'foobar:50000'
        event_receivers_dict = {}
        event_receivers_dict[event_receiver_address] = event_receiver

        event_subscription_servicer = mock.MagicMock()
        event_subscription_servicer.event_receivers_dict = event_receivers_dict

        event_queue = queue.Queue(maxsize=10)  # Empty queue.
        client_streamer = eventhub_stream_proxy_impl.ClientStreamer(
            event_subscription_servicer,
            event_queue,
            event_queue_get_batch_threshold=10)

        # When.
        with mock.patch.object(event_receiver,
                               'ReceiveEvents') as ReceiveEvents_method:
            client_streamer._stream()

        # Then.
        ReceiveEvents_method.assert_called_once()

    def test_stream_event_fail_on_unexpected_error(self):
        # Given.
        event_receivers_dict = {}
        event_receiver = mock.MagicMock()
        event_receiver_address = f'foobar:50001'
        event_receivers_dict[event_receiver_address] = event_receiver

        event_subscription_servicer = mock.MagicMock()
        event_subscription_servicer.event_receivers_dict = event_receivers_dict

        event_queue = queue.Queue(maxsize=10)
        event = event_pb2.Event()
        event_queue.put(event)

        client_streamer = eventhub_stream_proxy_impl.ClientStreamer(
            event_subscription_servicer,
            event_queue,
            event_queue_get_batch_threshold=10)

        with mock.patch.object(event_receiver,
                               'ReceiveEvents') as ReceiveEvents_method:
            with mock.patch.object(
                    event_subscription_servicer,
                    'unsubscribe_by_address') as unsubscribe_by_address_method:

                ReceiveEvents_method.side_effect = Exception(
                    'Something bad happened')
                # When.
                client_streamer._stream_events_to_subscribers([event])

        # Then.
        ReceiveEvents_method.assert_called_once()
        unsubscribe_by_address_method.assert_called_once()


if __name__ == '__main__':
    absltest.main()
