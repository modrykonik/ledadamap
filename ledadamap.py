#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mmap
import os
import struct


PERTURB_SHIFT = 5


class LedadaReadMap(object):

    def __init__(self, filepath):
        fd = os.open(filepath, os.O_RDONLY)
        self.buf = mmap.mmap(fd, 0, mmap.MAP_SHARED, mmap.PROT_READ)
        os.close(fd)
        if self.buf[:4] != 'LEDA':
            raise ValueError('Incorrect file format.')
        self.num_buckets = struct.unpack_from('I', self.buf, 4)[0]
        self.buckets_start = 8
        self.payload_start = self.buckets_start + self.num_buckets * 8

    def _grab_string(self, pointer):
        size = struct.unpack_from('H', self.buf, pointer)[0]
        return struct.unpack_from('%ds' % size, self.buf, pointer + 2)[0]

    def get(self, name, default=None):
        if isinstance(name, unicode):
          name = name.encode('utf8')
        hash_ = hash(name)

        idx = hash_ & (self.num_buckets - 1)
        j = idx
        perturb = abs(hash_)
        while True:
            key_pointer, value_pointer = struct.unpack_from('II', self.buf, self.buckets_start + idx * 8)
            if not key_pointer:
                return default
            if self._grab_string(key_pointer) == name:
                return self._grab_string(value_pointer)

            j = (5 * j) + 1 + perturb
            perturb >>= PERTURB_SHIFT
            idx = j & (self.num_buckets - 1)
