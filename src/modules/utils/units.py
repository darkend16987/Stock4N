"""Chuẩn hoá đơn vị giá."""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config


def price_to_vnd(price):
    """
    Giá vnstock tính theo nghìn đồng (VD 29.3 = 29,300đ) → đồng.
    Giá < config.PRICE_UNIT_CONFIG['threshold'] được coi là đơn vị nghìn đồng.
    """
    cfg = config.PRICE_UNIT_CONFIG
    return price * cfg['multiplier'] if price < cfg['threshold'] else price
