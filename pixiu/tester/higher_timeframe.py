"""Run-local aggregation of arrived records, without reading future rows."""

import numpy as np


class HigherTimeframeCache:
    def __init__(self, source, seconds):
        self.source = source
        self.seconds = seconds
        self.last_source_cursor = -1
        self.completed_bars = []
        self.forming_bar = None
        self.completed_revision = 0
        self.forming_revision = 0
        self.rows_consumed = 0
        self.rebuilds = 0
        self.snapshots_built = 0
        self._snapshot = None

    @property
    def revision(self):
        return self.completed_revision, self.forming_revision

    def advance(self, end):
        if end < 0 or end > len(self.source):
            raise ValueError('Invalid source cursor')
        if end <= self.last_source_cursor:
            self.last_source_cursor = -1
            self.completed_bars = []
            self.forming_bar = None
            self.completed_revision += 1
            self.forming_revision += 1
            self._snapshot = None
            self.rebuilds += 1
        for index in range(self.last_source_cursor + 1, end):
            row = self.source[index]
            if index and row['t'] < self.source[index - 1]['t']:
                raise ValueError('Source timestamps must be nondecreasing')
            bucket = np.floor(row['t'] / self.seconds) * self.seconds
            if self.forming_bar is None or bucket != self.forming_bar['t']:
                if self.forming_bar is not None:
                    self.completed_bars.append(self.forming_bar)
                    self.completed_revision += 1
                self.forming_bar = row.copy()
                self.forming_bar['t'] = bucket
            else:
                bar = self.forming_bar
                bar['h'] = np.maximum(bar['h'], row['h'])
                bar['l'] = np.minimum(bar['l'], row['l'])
                bar['v'] += row['v']
                for field in ('c', 'a', 'b'):
                    bar[field] = row[field]
            self.last_source_cursor = index
            self.rows_consumed += 1
            self.forming_revision += 1
            self._snapshot = None

    def snapshot(self):
        if self._snapshot is None:
            bars = self.completed_bars + ([self.forming_bar] if self.forming_bar is not None else [])
            # No spare capacity or future backing rows are exposed in this copy.
            self._snapshot = np.array(bars, dtype=self.source.dtype)
            self._snapshot.setflags(write=False)
            self.snapshots_built += 1
        return self._snapshot
