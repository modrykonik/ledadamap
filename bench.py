#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from ledadagen import LedadaGen
from ledadamap import LedadaReadMap


FILENAME = 'bench_output.leda'


def nice_duration(seconds):
    value = seconds
    if value > 1:
        return '{0:.3f} s'.format(seconds)
    value *= 1000
    if value > 1:
        return '{0:.3f} ms'.format(seconds * 1000)
    value *= 1000
    if value > 1:
        return '{0:.3f} us'.format(seconds * (1000 * 1000))
    return '{0:.3f} ns'.format(seconds * (1000 * 1000 * 1000))


def gen_map():
    ITEMS = 100000
    dct = {}
    for i in range(ITEMS):
        dct['key{0}'.format(i)] = 'value{0}'.format(i)

    gen = LedadaGen()
    gen.from_dict(dct)
    gen.write_to_file(open(FILENAME, 'wb'))


def main():
    gen_map()
    map1 = LedadaReadMap(FILENAME)

    RUNS = 100000

    # ledadamap, sequential keys
    start = time.time()
    for i in range(RUNS):
        map1.get(b'key%d' % i)
    end = time.time()
    loop_duration = (end - start) / RUNS
    print nice_duration(loop_duration)

    # ledadamap, static non-existing key
    start = time.time()
    for i in range(RUNS):
        map1.get(b'key785875858')
    end = time.time()
    loop_duration = (end - start) / RUNS
    print nice_duration(loop_duration)

    dct = {}
    for i in range(RUNS):
        dct[b'key%d' % i] = b'value%d' % i

    # python dict, sequential keys
    start = time.time()
    for i in range(RUNS):
        dct.get(b'key%d' % i)
    end = time.time()
    loop_duration = (end - start) / RUNS
    print nice_duration(loop_duration)

    # python dict, static non-existing key
    start = time.time()
    for i in range(RUNS):
        dct.get(b'key785875858')
    end = time.time()
    loop_duration = (end - start) / RUNS
    print nice_duration(loop_duration)


main()
