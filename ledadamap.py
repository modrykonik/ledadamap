#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import mmap
import os
import struct


PERTURB_SHIFT = 5


def stable_hash(str_value):
    if not str_value:
        return 0
    x = ord(str_value[0]) << 7
    for c in str_value:
        x = ctypes.c_long(1000003 * x).value
        x ^= ord(c)

    x ^= len(str_value)
    return x


class DirtyError(Exception):
    pass


class LedadaReadMap(object):

    def __init__(self, filepath):
        fd = os.open(filepath, os.O_RDONLY)
        self.buf = mmap.mmap(fd, 0, mmap.MAP_SHARED, mmap.PROT_READ)
        os.close(fd)
        if self.buf[:4] == 'LEDD':
            raise DirtyError('File is dirty.')
        if self.buf[:4] != 'LEDA':
            raise ValueError('Incorrect file format.')
        self.num_buckets = struct.unpack_from('I', self.buf, 4)[0]
        self.buckets_start = 8
        self.payload_start = self.buckets_start + self.num_buckets * 4

    def get(self, name, default=None):
        if self.buf[3] == 'D':
            raise DirtyError('File is dirty.')

        if isinstance(name, unicode):
            name = name.encode('utf8')

        hash_ = stable_hash(name)
        idx = hash_ & (self.num_buckets - 1)
        perturb = hash_
        if perturb < 0:
            perturb += 2 ** 64

        while True:
            chunk_pointer = struct.unpack_from('I', self.buf, self.buckets_start + idx * 4)[0]
            if not chunk_pointer:
                return default

            key_len, value_len = struct.unpack_from('HH', self.buf, chunk_pointer)
            key = struct.unpack_from('%ds' % key_len, self.buf, chunk_pointer + 4)[0]
            if key == name:
                return struct.unpack_from('%ds' % value_len, self.buf, chunk_pointer + 4 + key_len)[0]

            idx = (5 * idx) + 1 + perturb
            perturb >>= PERTURB_SHIFT
            idx &= (self.num_buckets - 1)
