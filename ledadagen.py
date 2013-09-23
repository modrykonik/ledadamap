#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import struct


PERTURB_SHIFT = 5
OVERSIZE_FACTOR = 4


class LedadaGen(object):

    def __init__(self):
        self._dict = {}
        self.buckets = []
        self.payload = ''
        self.key_pointers = []
        self.value_pointers = []

    def from_dict(self, dct):
        self._dict = dct

    def _to_utf(self, what, value):
        if isinstance(value, unicode):
            value = value.encode('utf8')
        elif not isinstance(value, str):
            raise TypeError('{0} needs to be a string or unicode.'.format(what))
        return value

    def _fill_buckets(self):
        print len(self._dict), 'items'
        value = len(self._dict) * OVERSIZE_FACTOR
        shift = 0
        while value > 0:
            value >>= 1
            shift += 1

        num_buckets = 1 << shift
        print num_buckets, 'buckets'
        self.buckets = [None] * num_buckets

        collisions = 0
        for key in self._dict:
            value = self._to_utf('value', self._dict[key])
            key = self._to_utf('key', key)

            idx = hash(key) & (num_buckets - 1)
            perturb = abs(hash(key))

            perturb = hash(key)
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
        print collisions, 'collisions'

    def _prepare_payload(self):
        header_size = 8
        buckets_size = len(self.buckets) * 8
        offset = header_size + buckets_size
        payload_items = []
        self.key_pointers = [0] * len(self.buckets)
        self.value_pointers = [0] * len(self.buckets)
        for idx, bucket in enumerate(self.buckets):
            if not bucket:
                continue

            self.key_pointers[idx] = offset
            payload_items.append(struct.pack('H', len(bucket[0])))
            payload_items.append(bucket[0])
            offset += 2 + len(bucket[0])

            self.value_pointers[idx] = offset
            payload_items.append(struct.pack('H', len(bucket[1])))
            payload_items.append(bucket[1])
            offset += 2 + len(bucket[1])

        self.payload = ''.join(payload_items)

    def write_to_file(self, fileobj):
        self._fill_buckets()
        self._prepare_payload()

        fileobj.seek(0)
        fileobj.truncate()
        data = ['LEDA']
        data.append(struct.pack('I', len(self.buckets)))
        for idx, bucket in enumerate(self.buckets):
            data.append(struct.pack('II', self.key_pointers[idx], self.value_pointers[idx]))
        data.append(self.payload)
        datastr = ''.join(data)
        PAGESIZE = 4096
        paddinglen = (PAGESIZE - (len(datastr) % PAGESIZE)) % PAGESIZE
        fileobj.write(''.join(datastr))
        fileobj.write('\x00' * paddinglen)
        fileobj.flush()


if __name__ == '__main__':
    # dct = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'key4': 'value4'}

    dct = {}
    for i in range(100000):
        dct['key{0}'.format(i)] = 'value{0}'.format(i)

    gen = LedadaGen()
    gen.from_dict(dct)
    gen.write_to_file(open('test_output.leda', 'wb'))
