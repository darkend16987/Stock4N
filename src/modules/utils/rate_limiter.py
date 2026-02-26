"""
Smart Rate Limiter for vnstock API

Prevents rate limit errors by tracking requests and auto-pausing
when approaching the limit.

Usage:
    from modules.utils.rate_limiter import RateLimiter

    limiter = RateLimiter(max_requests=60, time_window=60)

    with limiter:
        # Your API call here
        data = fetch_stock_data(symbol)
"""

import time
import threading
from datetime import datetime, timedelta
from collections import deque
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter with automatic backoff

    Features:
    - Tracks requests in sliding time window
    - Auto-pauses when approaching limit
    - Smart cooldown calculation
    - Progress reporting
    """

    def __init__(self, max_requests=60, time_window=60, buffer=5):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed per time window
            time_window: Time window in seconds (default: 60s = 1 minute)
            buffer: Safety buffer (pause at max_requests - buffer)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.buffer = buffer
        self.safe_limit = max_requests - buffer  # Pause at 55/60

        # Thread-safe request tracking
        self.request_times = deque()
        self.lock = threading.Lock()

        # Statistics
        self.total_requests = 0
        self.total_pauses = 0
        self.total_wait_time = 0

        logger.info(f"RateLimiter initialized: {max_requests} req/{time_window}s (buffer: {buffer})")

    def __enter__(self):
        """Context manager entry - check and wait if needed"""
        self._wait_if_needed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record request"""
        with self.lock:
            self.request_times.append(time.time())
            self.total_requests += 1

    def _clean_old_requests(self):
        """Remove requests outside the time window"""
        current_time = time.time()
        cutoff_time = current_time - self.time_window

        with self.lock:
            # Remove old requests
            while self.request_times and self.request_times[0] < cutoff_time:
                self.request_times.popleft()

    def _get_current_count(self):
        """Get number of requests in current time window"""
        self._clean_old_requests()
        with self.lock:
            return len(self.request_times)

    def _calculate_wait_time(self):
        """Calculate how long to wait before next request"""
        self._clean_old_requests()

        with self.lock:
            if len(self.request_times) < self.safe_limit:
                return 0  # No wait needed

            # Wait until oldest request expires
            oldest_request = self.request_times[0]
            wait_until = oldest_request + self.time_window
            wait_time = max(0, wait_until - time.time())

            return wait_time

    def _wait_if_needed(self):
        """Wait if approaching rate limit"""
        current_count = self._get_current_count()

        if current_count >= self.safe_limit:
            wait_time = self._calculate_wait_time()

            if wait_time > 0:
                self.total_pauses += 1
                self.total_wait_time += wait_time

                logger.warning("=" * 60)
                logger.warning("⚠️  RATE LIMIT APPROACHING")
                logger.warning("=" * 60)
                logger.warning(f"Current: {current_count}/{self.max_requests} requests")
                logger.warning(f"Pausing for {wait_time:.1f} seconds to avoid limit...")
                logger.warning(f"Resume at: {datetime.now() + timedelta(seconds=wait_time)}")
                logger.warning("=" * 60)

                # Countdown with progress
                self._countdown(wait_time)

                logger.info("✓ Resuming requests...")

    def _countdown(self, seconds):
        """Show countdown timer"""
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            remaining = max(0, seconds - elapsed)

            if remaining <= 0:
                break

            # Show progress bar
            progress = (elapsed / seconds) * 100
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            print(f"\r  [{bar}] {progress:.1f}% - {remaining:.0f}s remaining", end='', flush=True)
            time.sleep(1)

        print()  # New line after countdown

    def get_stats(self):
        """Get rate limiter statistics"""
        return {
            'total_requests': self.total_requests,
            'total_pauses': self.total_pauses,
            'total_wait_time': self.total_wait_time,
            'current_count': self._get_current_count(),
            'limit': self.max_requests
        }

    def print_stats(self):
        """Print statistics"""
        stats = self.get_stats()

        logger.info("=" * 60)
        logger.info("RATE LIMITER STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total requests: {stats['total_requests']}")
        logger.info(f"Total pauses: {stats['total_pauses']}")
        logger.info(f"Total wait time: {stats['total_wait_time']:.1f}s")
        logger.info(f"Current window: {stats['current_count']}/{stats['limit']}")
        logger.info("=" * 60)


class BatchProcessor:
    """
    Process items in batches with rate limiting

    Example:
        processor = BatchProcessor(
            items=symbols,
            process_fn=fetch_data,
            rate_limiter=limiter,
            batch_size=20
        )
        results = processor.run()
    """

    def __init__(self, items, process_fn, rate_limiter=None, batch_size=None):
        """
        Initialize batch processor

        Args:
            items: List of items to process
            process_fn: Function to process each item (must accept item as first arg)
            rate_limiter: RateLimiter instance (optional)
            batch_size: Items per batch (auto-calculated if None)
        """
        self.items = items
        self.process_fn = process_fn
        self.rate_limiter = rate_limiter or RateLimiter()

        # Auto-calculate batch size based on rate limit
        if batch_size is None:
            # Assume 3 API calls per item
            self.batch_size = max(1, (self.rate_limiter.safe_limit // 3))
        else:
            self.batch_size = batch_size

        logger.info(f"BatchProcessor initialized: {len(items)} items, batch_size={self.batch_size}")

    def run(self, *args, **kwargs):
        """
        Process all items in batches

        Returns:
            List of results (None for failed items)
        """
        results = []
        total_items = len(self.items)
        num_batches = (total_items + self.batch_size - 1) // self.batch_size

        logger.info("=" * 60)
        logger.info("BATCH PROCESSING START")
        logger.info("=" * 60)
        logger.info(f"Total items: {total_items}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Number of batches: {num_batches}")
        logger.info("=" * 60)

        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_items)
            batch_items = self.items[start_idx:end_idx]

            logger.info(f"Processing batch {batch_idx + 1}/{num_batches} ({len(batch_items)} items)...")

            batch_results = []
            for item in batch_items:
                try:
                    # Use rate limiter
                    with self.rate_limiter:
                        result = self.process_fn(item, *args, **kwargs)
                        batch_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {item}: {e}")
                    batch_results.append(None)

            results.extend(batch_results)

            # Progress report
            progress = (end_idx / total_items) * 100
            logger.info(f"✓ Batch {batch_idx + 1}/{num_batches} completed ({progress:.1f}% total)")

        logger.info("=" * 60)
        logger.info("BATCH PROCESSING COMPLETED")
        logger.info("=" * 60)

        # Print rate limiter stats
        self.rate_limiter.print_stats()

        return results


if __name__ == "__main__":
    # Test rate limiter
    print("Testing RateLimiter...")

    limiter = RateLimiter(max_requests=10, time_window=5, buffer=2)

    # Simulate 20 requests (should pause once)
    for i in range(20):
        with limiter:
            print(f"Request {i + 1}/20")
            time.sleep(0.1)  # Simulate API call

    limiter.print_stats()
