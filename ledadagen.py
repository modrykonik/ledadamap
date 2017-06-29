#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import mmap
import os
import random
import six
import struct
import cledadamap


PERTURB_SHIFT = 5
OVERSIZE_FACTOR = 4


class LedadaGen(object):

    def __init__(self):
        self._dict = {}
        self.buckets = []
        self.payload = b''
        self.chunk_pointers = []

    def from_dict(self, dct):
        self._dict = dct

    def _to_utf(self, what, value):
        if isinstance(value, six.text_type):
            value = value.encode('utf8')
        elif not isinstance(value, six.binary_type):
            raise TypeError('{0} needs to be a string or unicode.'.format(what))
        return value

    def _fill_buckets(self):
        logging.debug('{0} items'.format(len(self._dict)))
        value = len(self._dict) * OVERSIZE_FACTOR
        shift = 0
        while value > 0:
            value >>= 1
            shift += 1

        num_buckets = 1 << shift
        logging.debug('{0} buckets'.format(num_buckets))
        self.buckets = [None] * num_buckets

        collisions = 0
        for key in self._dict:
            value = self._to_utf('value', self._dict[key])
            key = self._to_utf('key', key)

            hash_ = cledadamap.stable_hash(key)
            idx = hash_ & (num_buckets - 1)
            perturb = hash_
            if perturb < 0:
                perturb += 2 ** 64

            while True:
                bucket = self.buckets[idx]
                if bucket is None:
                    break

                collisions += 1

                idx = (5 * idx) + 1 + perturb
                perturb >>= PERTURB_SHIFT
                idx &= (num_buckets - 1)

            bucket = (key, value)
            self.buckets[idx] = bucket
        logging.debug('{0} collisions'.format(collisions))

    def _prepare_payload(self):
        header_size = 8
        buckets_size = len(self.buckets) * 4
        offset = header_size + buckets_size
        payload_items = []
        self.chunk_pointers = [0] * len(self.buckets)
        for idx, bucket in enumerate(self.buckets):
            if not bucket:
                continue

            key, value = bucket
            self.chunk_pointers[idx] = offset
            payload_items.append(struct.pack('HH', len(key), len(value)))
            payload_items.append(key)
            payload_items.append(value)
            offset += 4 + len(key) + len(value)

        self.payload = b''.join(payload_items)

    def write_to_file(self, fileobj):
        self._fill_buckets()
        self._prepare_payload()

        fileobj.seek(0)
        fileobj.truncate()
        data = [b'LEDA']
        data.append(struct.pack('I', len(self.buckets)))
        for idx, bucket in enumerate(self.buckets):
            data.append(struct.pack('I', self.chunk_pointers[idx]))
        data.append(self.payload)
        datastr = b''.join(data)
        fileobj.write(datastr)
        PAGESIZE = 4096
        tailsize = len(datastr) & (PAGESIZE - 1)
        if tailsize:
            paddinglen = PAGESIZE - tailsize
            fileobj.write(b'\x00' * paddinglen)
        fileobj.flush()

    def overwrite_with_switch(self, filepath):
        while True:
            temp_filepath = '{0}.{1}'.format(filepath, random.randint(100000, 999999))
            try:
                fd = os.open(temp_filepath, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            except OSError as exc:
                if exc.errno == 17:     # 17 = file exists
                    continue
                raise
            break
        fileobj = os.fdopen(fd, 'wb')
        self.write_to_file(fileobj)

        buf = None
        try:
            oldfd = os.open(filepath, os.O_RDWR)
        except OSError as exc:
            if exc.errno != 2:          # 2 = no such file
                raise
            oldfd = None
        else:
            buf = mmap.mmap(oldfd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
            os.close(oldfd)

        os.rename(temp_filepath, filepath)

        if buf:
            buf[3] = 'D'
            buf.flush()
            buf.close()


if __name__ == '__main__':
    # dct = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'key4': 'value4'}

    dct = {}
    for i in range(10):
        dct['key{0}'.format(i)] = 'value{0}'.format(i)

    gen = LedadaGen()
    gen.from_dict(dct)
    # gen.write_to_file(open('test_output.leda', 'wb'))
    gen.overwrite_with_switch('test_output.leda')
