# Used for memory consumption calculations
#
# Copyright (C) 2025 VyOS Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import psutil
import pprint

from vyos.utils.cpu import get_core_count
from vyos.vpp.utils import (
    get_hugepages_info,
    human_memory_to_bytes,
    human_page_memory_to_bytes,
)


def available_memory(config: dict, defaults: dict) -> int:
    # We need to use a custom calculation of available memory
    # To reserve 4 GB for system and other (non-VPP) services
    settings = config['settings']
    hp_info = get_hugepages_info()
    pprint.pprint(hp_info)
    hp_size = hugepage_size(settings, defaults['hugepage_size'])
    nr_hps = hp_info['HugePages_Free']

    if os.path.exists('/tmp/vyos.smoketests.hint'):
        nr_hps = hugepage_count(settings, defaults['nr_hugepages'])

    mem_free = nr_hps * hp_size

    if config.get('effective'):
        # If there is an active VPP configuration, calculate how much it uses
        # And ignore its memory consumption
        mem_free += total_memory_required(
            settings=config['effective'], defaults=defaults
        )
    pprint.pprint(mem_free)
    return mem_free


def buffer_size(settings: dict, defaults: dict, **kwargs) -> int:
    cpus_count = kwargs.get('cpus_count', get_core_count())
    buffers_per_numa = int(
        settings.get('buffers', {}).get(
            'buffers_per_numa', defaults.get('buffers_per_numa')
        )
    )
    data_size = int(
        settings.get('buffers', {}).get('data_size', defaults.get('data_size'))
    )
    buffers_memory = buffers_per_numa * data_size * cpus_count
    return buffers_memory


def hugepage_count(settings: dict, default_nr_hugepages: int) -> int:
    return int(
        settings.get('host_resources', {}).get('nr_hugepages', default_nr_hugepages)
    )


def netlink_buffer_size(settings: dict, default_buffer: int) -> int:
    return int(settings.get('lcp', {}).get('rx_buffer_size', default_buffer))


def hugepage_size(settings: dict, default_hugepage: str):
    hp_size = settings.get('memory', {}).get('default_hugepage_size', default_hugepage)
    return human_page_memory_to_bytes(hp_size)


def main_heap_page_size(settings: dict, default_main_page: str) -> int:
    heap_page_size = settings.get('memory', {}).get(
        'main_heap_page_size', default_main_page
    )
    return human_page_memory_to_bytes(heap_page_size)


def memory_main_heap(settings: dict, default_heap_size: str) -> int:
    heap_size = settings.get('memory', {}).get('main_heap_size')
    if not heap_size:
        heap_size = default_heap_size
    return human_memory_to_bytes(heap_size)


def ipv6_heap_size(settings: dict, default_ipv6_heap: str) -> int:
    heap_size = settings.get('ipv6', {}).get('heap_size')
    if not heap_size:
        heap_size = default_ipv6_heap
    return human_memory_to_bytes(heap_size)


def statseg_size(settings: dict, default_statseg_heap: str) -> int:
    statseg_memory = settings.get('statseg', {}).get('size')
    if not statseg_memory:
        statseg_memory = default_statseg_heap
    return human_memory_to_bytes(statseg_memory)


def statseg_page_size(settings: dict) -> int:
    page_size = settings.get('statseg', {}).get('page_size', 'default')
    return human_page_memory_to_bytes(page_size)


def total_memory_required(settings: dict, defaults: dict) -> int:
    mem_required = 0
    mem_stats = {
        'memory_buffers': buffer_size(settings, defaults),
        'heap_size': memory_main_heap(settings, defaults.get('main_heap_size')),
        'statseg_size': statseg_size(settings, defaults.get('statseg_heap_size')),
        'ipv6_heap_size': ipv6_heap_size(settings, defaults.get('ipv6_heap_size')),
    }

    for stat in mem_stats:
        mem_required += mem_stats[stat]
    return mem_required
