"""
Sổ nhật ký quyết định của hội đồng (append-only JSONL) - nền tảng cho forward-test.

Mỗi dòng ghi đủ để SAU NÀY đối chiếu với kết quả thực: ngày dữ liệu, dữ kiện đã đưa vào, từng vai trò nói gì,
quyết định cuối, khuyến nghị của hệ thống tại thời điểm đó, giá. Idempotent theo (as_of, symbol, prompt_version).
"""
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class Ledger:
    def __init__(self, path=None):
        self.path = path or config.COMMITTEE_CONFIG['ledger_file']

    def _read(self):
        if not os.path.exists(self.path):
            return []
        entries = []
        with open(self.path, encoding='utf-8') as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Ledger dòng {n} hỏng, bỏ qua")
        return entries

    def entries(self):
        """Toàn bộ bản ghi (mọi trạng thái), theo thứ tự ghi."""
        return self._read()

    def find(self, as_of, symbol, prompt_version, facts_hash=None):
        """Bản ghi OK gần nhất khớp khoá (và dữ kiện nếu truyền facts_hash); None nếu chưa có."""
        match = None
        for e in self._read():
            if (e.get('as_of') == str(as_of) and e.get('symbol') == symbol
                    and e.get('prompt_version') == prompt_version and e.get('status') == 'OK'
                    and (facts_hash is None or e.get('facts_hash') == facts_hash)):
                match = e
        return match

    def append(self, entry):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + '\n')
