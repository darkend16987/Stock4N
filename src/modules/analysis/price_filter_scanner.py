"""
Price Filter Scanner - Quét toàn bộ thị trường chứng khoán Việt Nam
Lọc cổ phiếu theo điều kiện:
  - Giá đóng cửa < SMA200
  - Thanh khoản trung bình 20 phiên >= 500.000 CP
  - PE < 20
  - PB < 5
"""
import pandas as pd
import numpy as np
import time
import os
import sys
import re
import json
from datetime import datetime, timedelta
from threading import Lock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger
from modules.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class PriceFilterScanner:
    """
    Quét toàn bộ mã cổ phiếu Việt Nam và lọc theo tiêu chí:
    - Close < SMA200
    - Avg Volume 20 >= 500,000
    - PE < 20
    - PB < 5

    Có cơ chế batch + rate limit để không bị die khi quét ~1700 mã.
    """

    # Filter defaults
    DEFAULT_SMA_PERIOD = 200
    DEFAULT_VOL_PERIOD = 20
    DEFAULT_MIN_AVG_VOL = 500_000
    DEFAULT_MAX_PE = 20
    DEFAULT_MAX_PB = 5

    # Batch config — tuned for 55 req/min API key
    # Each symbol = ~2 API calls (price + ratio), safe_limit = 45/min
    # → batch 20 symbols = ~40 calls, fits within 1 minute window
    BATCH_SIZE = 20          # Symbols per batch
    BATCH_DELAY = 5          # Seconds between batches (RateLimiter handles throttling)
    RETRY_DELAY = 65         # Seconds to wait on rate limit error
    MAX_RETRIES = 3          # Max retries per symbol

    def __init__(self):
        self.logger_lock = Lock()
        self.results = []
        self.errors = []
        self.progress_file = os.path.join(config.DATA_DIR, 'price_filter_progress.json')
        self.result_file = os.path.join(config.PROCESSED_DIR, 'price_filter_results.csv')

        # Rate limiter: conservative 55 req/min for safety
        api_key = config.VNSTOCK_CONFIG.get('api_key') or os.environ.get('VNSTOCK_API_KEY')
        if api_key and api_key.startswith('vnstock_'):
            self.rate_limiter = RateLimiter(max_requests=55, time_window=60, buffer=10)
        else:
            self.rate_limiter = RateLimiter(max_requests=18, time_window=60, buffer=5)

    def _save_progress(self, processed_symbols, batch_idx, total_batches):
        """Save progress to resume if interrupted."""
        progress = {
            'processed_symbols': processed_symbols,
            'batch_idx': batch_idx,
            'total_batches': total_batches,
            'timestamp': datetime.now().isoformat(),
            'results_count': len(self.results),
            'errors_count': len(self.errors)
        }
        try:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save progress: {e}")

    def _load_progress(self):
        """Load previous progress if exists."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _clear_progress(self):
        """Clear progress file after completion."""
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception:
                pass

    def get_all_symbols(self):
        """Get all stock symbols from Vietnam market."""
        try:
            from vnstock import Listing
            listing = Listing()
            df = listing.all_symbols()
            if df is not None and not df.empty:
                symbols = df['symbol'].tolist()
                logger.info(f"Found {len(symbols)} stock symbols on Vietnam market")
                return symbols
        except Exception as e:
            logger.error(f"Failed to get all symbols via Listing: {e}")

        # Fallback: use config symbols
        logger.warning("Falling back to VN100_SYMBOLS from config")
        return list(set(config.VN100_SYMBOLS))

    def _parse_rate_limit_wait(self, error_msg):
        """Parse wait time from rate limit error message."""
        match = re.search(r'sau (\d+) giây', str(error_msg))
        if match:
            return int(match.group(1)) + 5
        return self.RETRY_DELAY

    def _fetch_price_data(self, symbol, source='VCI'):
        """Fetch price history for a symbol (last 250 trading days)."""
        from vnstock import Vnstock

        end_date = datetime.now().strftime('%Y-%m-%d')
        # Need ~250 trading days for SMA200
        start_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')

        stock = Vnstock().stock(symbol=symbol, source=source)
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        return df

    def _fetch_ratio_data(self, symbol, source='VCI'):
        """Fetch financial ratios (PE, PB) for a symbol."""
        from vnstock import Vnstock

        stock = Vnstock().stock(symbol=symbol, source=source)
        df = stock.company.ratio_summary()
        return df

    def _safe_api_call(self, func, symbol, call_type='data'):
        """Make an API call with rate limiting and retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                with self.rate_limiter:
                    result = func()
                return result
            except Exception as e:
                error_str = str(e).lower()

                # Rate limit hit
                if 'rate limit' in error_str or '429' in error_str or 'quá nhiều request' in error_str:
                    wait_time = self._parse_rate_limit_wait(str(e))
                    logger.warning(f"Rate limit hit for {symbol} ({call_type}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                # Not found - don't retry
                if '404' in error_str or 'not found' in error_str or 'không tìm thấy' in error_str:
                    return None

                # Other errors
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = 2 * (attempt + 1)
                    logger.debug(f"Retry {attempt+1}/{self.MAX_RETRIES} for {symbol} ({call_type}): {e}")
                    time.sleep(wait_time)
                else:
                    logger.debug(f"All retries failed for {symbol} ({call_type}): {e}")

        return None

    def _process_symbol(self, symbol, idx, total):
        """Process a single symbol: fetch data and check filter criteria."""
        try:
            # 1. Fetch price data
            price_df = self._safe_api_call(
                lambda: self._fetch_price_data(symbol),
                symbol, 'price'
            )

            if price_df is None or price_df.empty:
                return None

            # Ensure we have enough data for SMA200
            if len(price_df) < self.DEFAULT_SMA_PERIOD:
                return None

            # Determine column names (vnstock can have different column names)
            close_col = None
            vol_col = None
            for c in price_df.columns:
                cl = c.lower()
                if cl in ('close', 'gia_dong_cua'):
                    close_col = c
                elif cl in ('volume', 'khoi_luong'):
                    vol_col = c

            if close_col is None or vol_col is None:
                # Try common patterns
                if 'close' in price_df.columns:
                    close_col = 'close'
                if 'volume' in price_df.columns:
                    vol_col = 'volume'

            if close_col is None or vol_col is None:
                logger.debug(f"{symbol}: Cannot identify close/volume columns: {list(price_df.columns)}")
                return None

            close_price = float(price_df[close_col].iloc[-1])
            sma200 = float(price_df[close_col].rolling(self.DEFAULT_SMA_PERIOD).mean().iloc[-1])

            if pd.isna(sma200):
                return None

            # Check condition 1: Close < SMA200
            if close_price >= sma200:
                return None

            # Check condition 2: Average volume 20 sessions >= 500,000
            avg_vol_20 = float(price_df[vol_col].tail(self.DEFAULT_VOL_PERIOD).mean())
            if avg_vol_20 < self.DEFAULT_MIN_AVG_VOL:
                return None

            # 2. Fetch PE/PB ratios
            time.sleep(0.3)  # Small gap between API calls
            ratio_df = self._safe_api_call(
                lambda: self._fetch_ratio_data(symbol),
                symbol, 'ratio'
            )

            pe = None
            pb = None

            if ratio_df is not None and not ratio_df.empty:
                # ratio_summary() returns a DataFrame - find PE and PB
                for c in ratio_df.columns:
                    cl = c.lower()
                    if cl in ('pe', 'p/e', 'price_to_earning', 'price_earning'):
                        try:
                            pe = float(ratio_df[c].iloc[-1])
                        except (ValueError, TypeError):
                            pass
                    elif cl in ('pb', 'p/b', 'price_to_book', 'price_book'):
                        try:
                            pb = float(ratio_df[c].iloc[-1])
                        except (ValueError, TypeError):
                            pass

            # If we couldn't get PE/PB from ratio_summary, skip
            if pe is None or pb is None or pd.isna(pe) or pd.isna(pb):
                return None

            # Check condition 3: PE < 20
            if pe >= self.DEFAULT_MAX_PE or pe <= 0:
                return None

            # Check condition 4: PB < 5
            if pb >= self.DEFAULT_MAX_PB or pb <= 0:
                return None

            # All conditions met!
            result = {
                'Symbol': symbol,
                'Close': round(close_price, 2),
                'SMA200': round(sma200, 2),
                'Pct_Below_SMA200': round((close_price - sma200) / sma200 * 100, 2),
                'Avg_Vol_20': int(avg_vol_20),
                'PE': round(pe, 2),
                'PB': round(pb, 2),
                'Scan_Date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }

            with self.logger_lock:
                logger.info(f"  MATCH {symbol}: Close={close_price:.0f} < SMA200={sma200:.0f}, "
                           f"Vol={avg_vol_20:,.0f}, PE={pe:.1f}, PB={pb:.1f}")

            return result

        except Exception as e:
            with self.logger_lock:
                logger.debug(f"Error processing {symbol}: {e}")
            return None

    def run_scan(self, symbols=None, resume=True):
        """
        Run full market scan with batching and rate limit handling.

        Args:
            symbols: List of symbols to scan (None = all market)
            resume: Resume from last progress if available

        Returns:
            pd.DataFrame with matching stocks
        """
        if symbols is None:
            symbols = self.get_all_symbols()

        # Check for resume
        processed_set = set()
        if resume:
            progress = self._load_progress()
            if progress and progress.get('processed_symbols'):
                processed_set = set(progress['processed_symbols'])
                logger.info(f"Resuming scan: {len(processed_set)} symbols already processed")

                # Load existing results
                if os.path.exists(self.result_file):
                    try:
                        existing = pd.read_csv(self.result_file)
                        self.results = existing.to_dict('records')
                        logger.info(f"Loaded {len(self.results)} existing results")
                    except Exception:
                        pass

        # Filter out already processed symbols
        remaining = [s for s in symbols if s not in processed_set]
        total_symbols = len(symbols)
        total_remaining = len(remaining)

        logger.info("=" * 65)
        logger.info("  PRICE FILTER SCANNER - FULL MARKET SCAN")
        logger.info("=" * 65)
        logger.info(f"  Total symbols   : {total_symbols}")
        logger.info(f"  Already processed: {len(processed_set)}")
        logger.info(f"  Remaining        : {total_remaining}")
        logger.info(f"  Batch size       : {self.BATCH_SIZE}")
        logger.info(f"  Conditions:")
        logger.info(f"    - Close < SMA{self.DEFAULT_SMA_PERIOD}")
        logger.info(f"    - Avg Volume {self.DEFAULT_VOL_PERIOD} >= {self.DEFAULT_MIN_AVG_VOL:,}")
        logger.info(f"    - PE < {self.DEFAULT_MAX_PE}")
        logger.info(f"    - PB < {self.DEFAULT_MAX_PB}")
        logger.info("=" * 65)

        if total_remaining == 0:
            logger.info("All symbols already processed!")
            return pd.DataFrame(self.results)

        # Split into batches
        batches = []
        for i in range(0, total_remaining, self.BATCH_SIZE):
            batches.append(remaining[i:i + self.BATCH_SIZE])

        total_batches = len(batches)
        est_minutes = total_batches * (self.BATCH_DELAY / 60 + 0.5)
        logger.info(f"  Estimated time   : ~{est_minutes:.0f} minutes ({total_batches} batches)")
        logger.info("=" * 65)

        all_processed = list(processed_set)

        for batch_idx, batch in enumerate(batches):
            batch_start = time.time()
            logger.info(f"\n--- Batch {batch_idx + 1}/{total_batches} ({len(batch)} symbols) ---")

            for sym_idx, symbol in enumerate(batch):
                global_idx = len(all_processed) + sym_idx
                try:
                    result = self._process_symbol(symbol, global_idx, total_symbols)
                    if result is not None:
                        self.results.append(result)
                except Exception as e:
                    logger.error(f"Unhandled error for {symbol}: {e}")
                    self.errors.append({'symbol': symbol, 'error': str(e)})

            # Mark batch as processed
            all_processed.extend(batch)

            # Save progress after each batch
            self._save_progress(all_processed, batch_idx + 1, total_batches)

            # Save intermediate results
            if self.results:
                df_results = pd.DataFrame(self.results)
                os.makedirs(os.path.dirname(self.result_file), exist_ok=True)
                df_results.to_csv(self.result_file, index=False, encoding='utf-8-sig')

            # Progress report
            elapsed = time.time() - batch_start
            pct_done = len(all_processed) / total_symbols * 100
            logger.info(f"  Batch {batch_idx + 1}/{total_batches} done in {elapsed:.1f}s | "
                       f"Progress: {pct_done:.1f}% | Matches so far: {len(self.results)}")

            # Wait between batches (except last batch)
            if batch_idx < total_batches - 1:
                logger.info(f"  Waiting {self.BATCH_DELAY}s before next batch (rate limit cooldown)...")
                time.sleep(self.BATCH_DELAY)

        # Final save
        if self.results:
            df_results = pd.DataFrame(self.results)
            df_results = df_results.sort_values('Pct_Below_SMA200', ascending=True)
            os.makedirs(os.path.dirname(self.result_file), exist_ok=True)
            df_results.to_csv(self.result_file, index=False, encoding='utf-8-sig')
        else:
            df_results = pd.DataFrame()

        # Clear progress
        self._clear_progress()

        # Print summary
        self._print_summary(df_results, total_symbols)

        return df_results

    def _print_summary(self, df_results, total_scanned):
        """Print scan summary."""
        logger.info("\n" + "=" * 65)
        logger.info("  SCAN COMPLETED")
        logger.info("=" * 65)
        logger.info(f"  Total scanned : {total_scanned}")
        logger.info(f"  Matches found : {len(df_results)}")
        logger.info(f"  Errors        : {len(self.errors)}")

        if not df_results.empty:
            logger.info(f"\n  Results saved to: {self.result_file}")
            logger.info("\n  TOP MATCHES:")
            logger.info("-" * 65)
            for _, row in df_results.head(20).iterrows():
                logger.info(
                    f"  {row['Symbol']:6s} | Close: {row['Close']:>10,.0f} | "
                    f"SMA200: {row['SMA200']:>10,.0f} | "
                    f"Vol: {row['Avg_Vol_20']:>12,} | "
                    f"PE: {row['PE']:>6.1f} | PB: {row['PB']:>5.1f}"
                )
            logger.info("-" * 65)

        logger.info("=" * 65)

    def get_latest_results(self):
        """Load latest scan results from file."""
        if os.path.exists(self.result_file):
            try:
                return pd.read_csv(self.result_file)
            except Exception:
                pass
        return pd.DataFrame()

    def get_scan_status(self):
        """Get current scan status (for UI)."""
        progress = self._load_progress()
        if progress:
            return {
                'status': 'running',
                'processed': len(progress.get('processed_symbols', [])),
                'matches': progress.get('results_count', 0),
                'errors': progress.get('errors_count', 0),
                'last_update': progress.get('timestamp', ''),
                'batch': f"{progress.get('batch_idx', 0)}/{progress.get('total_batches', 0)}"
            }
        return {'status': 'idle'}
