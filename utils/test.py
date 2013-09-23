#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from ledadagen import LedadaGen
# from ledadamap import LedadaReadMap
from cledadamap import LedadaReadMap


FILENAME = 'bench_output.leda'
ITEMS = 100000


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
    dct = {}
    for i in range(ITEMS):
        dct['key{0}'.format(i)] = 'value{0}'.format(i)

    gen = LedadaGen()
    gen.from_dict(dct)
    gen.write_to_file(open(FILENAME, 'wb'))


def main():
    gen_map()
    map1 = LedadaReadMap(FILENAME)

    RUNS = 1

    # print map1.get(b'key152')
    # print map1.get(b'key0')
    # print map1.get(b'key8')
    # print map1.get(b'key832554')
    # return

    import itertools
    one_run = xrange(ITEMS)
    items = itertools.chain(*([one_run] * RUNS))

    # ledadamap, sequential keys
    start = time.time()
    for i in items:
        key = b'key%d' % i
        value = map1.get(key)
        if value != 'value%d' % i:
            print "Wrong value for key '%s'" % key
            print value
    end = time.time()
    len_items = ITEMS * RUNS
    loop_duration = (end - start) / len_items
    print nice_duration(loop_duration)


main()
