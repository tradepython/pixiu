"""Version-checked JSON projections with independently mutable results."""

from collections import OrderedDict
import copy
import sys


def normalize_data_path(path):
    if not isinstance(path, (list, tuple)):
        raise TypeError('path must be a list or tuple of string keys and non-negative integer indexes')
    parts = tuple(path)
    for part in parts:
        if type(part) not in (str, int):
            raise TypeError('path components must be strings or integers, not booleans or other objects')
        if type(part) is int and part < 0:
            raise ValueError('path indexes must be non-negative')
    return parts


def _select(data, path):
    for part in path:
        if isinstance(data, dict):
            if type(part) is not str:
                raise TypeError('JSON object path components must be string keys')
        elif isinstance(data, list):
            if type(part) is not int:
                raise TypeError('JSON array path components must be integer indexes')
        else:
            raise TypeError('Cannot traverse a scalar or null JSON value')
        data = data[part]
    return data


def _retained_size(key, raw, value, limit):
    # Bound retained payloads, including dictionary keys, rather than just JSON
    # text length. Stop walking as soon as admission is no longer possible.
    size = sys.getsizeof((None, None, None, None))
    stack = [key, raw, value]
    seen = set()
    while stack:
        item = stack.pop()
        identity = id(item)
        if identity in seen:
            continue
        seen.add(identity)
        size += sys.getsizeof(item)
        if size > limit:
            return size
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    return size


class DataProjectionCache:
    """Cache private decode trees; callers receive only copied projections.

    Keys are provider-resolved storage namespaces. The provider must fetch the
    current raw value before every call. Mutable/non-string inputs are not cached.
    """

    def __init__(self, max_entries=32, max_bytes=16 * 1024 * 1024):
        if max_entries < 0 or max_bytes < 0:
            raise ValueError('Cache limits must be non-negative')
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries = OrderedDict()
        self.estimated_bytes = 0
        self.hits = 0
        self.misses = 0

    @property
    def entry_count(self):
        return len(self._entries)

    def clear(self):
        self._entries.clear()
        self.estimated_bytes = 0
        self.hits = self.misses = 0

    def discard(self, key):
        entry = self._entries.pop(key, None)
        if entry is not None:
            self.estimated_bytes -= entry[3]

    def load(self, key, raw, path, decoder):
        path = normalize_data_path(path)
        entry = self._entries.get(key)
        if entry is not None and type(raw) is str and entry[0] is raw and entry[1] is decoder:
            self._entries.move_to_end(key)
            self.hits += 1
            tree = entry[2]
        else:
            # Invalidate before decoding so a malformed new version can never
            # fall back to a previously valid tree or conceal its parser error.
            self.discard(key)
            self.misses += 1
            tree = decoder(raw)
            if type(raw) is str and self.max_entries and self.max_bytes:
                size = _retained_size(key, raw, tree, self.max_bytes)
                if size <= self.max_bytes:
                    while (len(self._entries) >= self.max_entries or
                           self.estimated_bytes + size > self.max_bytes):
                        oldest = next(iter(self._entries))
                        self.discard(oldest)
                    self._entries[key] = (raw, decoder, tree, size)
                    self.estimated_bytes += size
        return copy.deepcopy(_select(tree, path))
