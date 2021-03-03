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

# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,protected-access,no-self-use
import queue

import mock
from absl.testing import absltest

from eventhub_stream_proxy import eventhub_stream_proxy_impl
from proto import event_pb2


class EventSubscriptionServicerTestCase(absltest.TestCase):

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

    def test_event_hub_events_passed_to_queue(self):
        # Given.
        event_queue = queue.Queue(maxsize=10)
        event_hub_capture = eventhub_stream_proxy_impl.EventHubCapture(
            event_hub_info={
                'event_hub_conn_str': 'Endpoint=sb://FQDN/;'
                                      'SharedAccessKeyName=KeyName;'
                                      'SharedAccessKey=KeyValue',
                'event_hub_name': 'event_hub_name',
                'event_hub_consumer_group': 'event_hub_consumer_group'
            },
            event_queue=event_queue,
            event_queue_put_timeout_sec=1)

        event_hub_capture._receive_eventhub_client = mock.MagicMock()

        eventhub_event = mock.MagicMock()
        eventhub_event.body_as_str = mock.MagicMock(
            return_value='Simple EventHub event')

        event_hub_capture._receive_eventhub_client.receive = mock.MagicMock(
            return_value=[eventhub_event])

        # When.
        event_hub_capture._on_event(event=eventhub_event)

        # Then.
        event_from_queue = event_queue.get()
        self.assertEquals(event_from_queue.content, 'Simple EventHub event')


class ClientStreamerTestCase(absltest.TestCase):

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
        event_receivers_dict = {event_receiver_address: event_receiver}

        event_subscription_servicer = mock.MagicMock()
        event_subscription_servicer.event_receivers_dict = event_receivers_dict

        event_queue = queue.Queue(maxsize=10)  # Empty queue.
        client_streamer = eventhub_stream_proxy_impl.ClientStreamer(
            event_subscription_servicer,
            event_queue,
            event_queue_get_batch_threshold=10)

        # When.
        with mock.patch.object(event_receiver,
                               'ReceiveEvents') as receive_events_method:
            client_streamer._stream()

        # Then.
        receive_events_method.assert_called_once()

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
                               'ReceiveEvents') as receive_events_method:
            with mock.patch.object(
                    event_subscription_servicer,
                    'unsubscribe_by_address') as unsubscribe_by_address_method:
                receive_events_method.side_effect = Exception(
                    'Something bad happened')
                # When.
                client_streamer._stream_events_to_subscribers([event])

        # Then.
        receive_events_method.assert_called_once()
        unsubscribe_by_address_method.assert_called_once()


if __name__ == '__main__':
    absltest.main()
