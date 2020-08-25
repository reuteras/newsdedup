#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test code for newsdedup.py"""
from newsdedup import read_configuration, init_ignore_list


def test_init_ignore_list():
    """Test init_ignore_list()"""
    config = read_configuration("newsdedup.cfg.default")
    assert init_ignore_list(config) == ['1', '2', '3']
