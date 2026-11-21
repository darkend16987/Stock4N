"""
Chia dữ liệu theo THỜI GIAN có purge - thay cho train_test_split ngẫu nhiên.

Vì sao: nhãn của mẫu ngày d dùng giá đến d+h phiên, nên các mẫu liền kề có nhãn chồng lấn. Chia ngẫu nhiên đưa
mẫu "hàng xóm" của tập test vào tập train → độ chính xác bị thổi phồng. Dữ liệu gộp nhiều mã còn rò rỉ chéo mã
(cùng ngày, các mã cùng chịu một cú sốc thị trường).

Quy tắc: tập train chỉ gồm các ngày mà cửa sổ nhãn [d, d+h] kết thúc TRƯỚC ngày đầu của khối test.
(Chỉ huấn luyện trên quá khứ nên không cần embargo phía sau.)
"""
import numpy as np
import pandas as pd


def _date_positions(dates):
    """Map ngày → vị trí trong lịch giao dịch chung (các ngày duy nhất, đã sort)."""
    unique = np.array(sorted(pd.to_datetime(pd.Series(dates)).dt.normalize().unique()))
    return unique, {d: i for i, d in enumerate(unique)}


def purged_time_split(dates, horizon, test_size=0.2):
    """
    Một lần chia: test = test_size phần ngày cuối; train = các ngày kết thúc cửa sổ nhãn trước khi test bắt đầu.
    Returns (train_mask, test_mask) theo thứ tự của `dates`.
    """
    dates = pd.to_datetime(pd.Series(dates)).dt.normalize().reset_index(drop=True)
    unique, pos = _date_positions(dates)
    cut = int(len(unique) * (1 - test_size))
    if cut <= horizon or cut >= len(unique):
        raise ValueError("Không đủ ngày để chia train/test có purge")
    p = dates.map(pos).to_numpy()
    return p < cut - horizon, p >= cut


class PurgedWalkForward:
    """
    Walk-forward mở rộng dần: khối test thứ k nằm sau khối train; train bị cắt `horizon` phiên cuối (purge).
    """

    def __init__(self, n_splits=5, horizon=20, min_train_dates=250):
        self.n_splits, self.horizon, self.min_train_dates = n_splits, horizon, min_train_dates

    def split(self, dates):
        dates = pd.to_datetime(pd.Series(dates)).dt.normalize().reset_index(drop=True)
        unique, pos = _date_positions(dates)
        n = len(unique)
        if n - self.min_train_dates < self.n_splits * 5:
            raise ValueError(f"Chỉ có {n} ngày, không đủ cho min_train_dates={self.min_train_dates} "
                             f"và {self.n_splits} khối kiểm tra")
        bounds = np.linspace(self.min_train_dates, n, self.n_splits + 1).astype(int)
        p = dates.map(pos).to_numpy()
        for k in range(self.n_splits):
            a, b = bounds[k], bounds[k + 1]
            train = p < a - self.horizon
            test = (p >= a) & (p < b)
            if train.sum() and test.sum():
                yield np.where(train)[0], np.where(test)[0]
