#  Copyright 2018-2020 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted
"""Standard collections enhanced with useful features."""

import collections
import threading


class ThreadSafeMap(collections.MutableMapping):
    """ Class implementing map in a thread safe way
        - by locking access to storage when operating on it."""

    def __init__(self, *args, **kwargs):
        self.lock = threading.Lock()
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        with self.lock:
            return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        with self.lock:
            self.store[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        with self.lock:
            del self.store[self.__keytransform__(key)]

    def __iter__(self):
        with self.lock:
            return iter(self.store)

    def __len__(self):
        with self.lock:
            return len(self.store)

    def __keytransform__(self, key):
        # pylint: disable=no-self-use
        return key
