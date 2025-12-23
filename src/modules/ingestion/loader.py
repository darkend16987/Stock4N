import pandas as pd
import time
import os
import random
from datetime import datetime
import sys
import vnstock

# Thêm đường dẫn src vào system path để import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger
from modules.utils.exceptions import (
    APIRateLimitException,
    APISourceUnavailableException,
    InvalidSymbolException
)
from modules.utils.validator import DataValidator

logger = get_logger(__name__)


class VNStockLoader:
    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir = data_dir
        self.use_legacy = hasattr(vnstock, 'stock_historical_data')
        self.validator = DataValidator()

        if not self.use_legacy:
            logger.info("Detected vnstock v3.x (OOP Mode)")
        else:
            logger.info("Detected vnstock v2.x (Legacy Mode)")

    def _get_file_path(self, symbol, data_type):
        return os.path.join(self.data_dir, f"{symbol}_{data_type}.csv")

    def _load_from_cache(self, file_path, max_age_days=1):
        """Load data from cache if it exists and is fresh enough"""
        if os.path.exists(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            age = (datetime.now() - file_time).days
            if age < max_age_days:
                logger.debug(f"Loading from cache: {file_path} (age: {age} days)")
                return pd.read_csv(file_path)
        return None

    def _save_to_cache(self, df, file_path):
        """Save data to cache"""
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False)
            logger.debug(f"Saved to cache: {file_path}")

    def _retry_with_backoff(self, func, symbol, max_attempts=None, *args, **kwargs):
        """
        Retry a function with exponential backoff

        Args:
            func: Function to retry
            symbol: Stock symbol (for logging)
            max_attempts: Maximum retry attempts (from config if None)
            *args, **kwargs: Arguments to pass to func

        Returns:
            Function result or None on failure
        """
        if max_attempts is None:
            max_attempts = config.API_RETRY['max_attempts']

        initial_wait = config.API_RETRY['initial_wait']
        max_wait = config.API_RETRY['max_wait']
        exponential_base = config.API_RETRY['exponential_base']

        for attempt in range(max_attempts):
            try:
                result = func(*args, **kwargs)
                if result is not None and not result.empty:
                    if attempt > 0:
                        logger.info(f"✓ Retry successful for {symbol} on attempt {attempt + 1}")
                    return result
            except Exception as e:
                error_str = str(e)

                # Check for rate limit
                if "rate limit" in error_str.lower() or "429" in error_str:
                    logger.warning(f"Rate limit hit for {symbol}, cooling down...")
                    time.sleep(config.RATE_LIMIT['cooldown_on_limit'])
                    continue

                # Check for not found (404) - don't retry
                if "404" in error_str or "not found" in error_str.lower():
                    logger.debug(f"Data not found for {symbol}: {error_str}")
                    return None

                # For other errors, use exponential backoff
                if attempt < max_attempts - 1:
                    wait_time = min(initial_wait * (exponential_base ** attempt), max_wait)
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {symbol}: {error_str}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_attempts} attempts failed for {symbol}: {error_str}")

        return None

    def get_price_data(self, symbol):
        """
        Lấy dữ liệu giá với cơ chế Fallback đa nguồn và retry logic
        """
        # Validate symbol first
        try:
            self.validator.validate_symbol(symbol)
        except InvalidSymbolException as e:
            logger.error(f"Invalid symbol: {e}")
            return None

        file_path = self._get_file_path(symbol, "price")
        cache_expiry = config.CACHE_EXPIRY['price']

        # Check cache
        cached = self._load_from_cache(file_path, max_age_days=cache_expiry)
        if cached is not None:
            logger.debug(f"Using cached price data for {symbol}")
            return cached

        if self.use_legacy:
            # Legacy mode (vnstock v2.x)
            def fetch_legacy():
                return vnstock.stock_historical_data(
                    symbol=symbol,
                    start_date=config.START_DATE,
                    end_date=config.TODAY,
                    resolution='1D',
                    type='stock'
                )

            df = self._retry_with_backoff(fetch_legacy, symbol)
            if df is not None and not df.empty:
                # Validate before saving
                is_valid, message = self.validator.validate_price_data(df, symbol)
                if is_valid:
                    self._save_to_cache(df, file_path)
                    return df
                else:
                    logger.warning(f"Price data validation failed for {symbol}: {message}")
            return None

        else:
            # Modern mode (vnstock v3.x) - fallback through multiple sources
            from vnstock import Vnstock
            sources = config.DATA_SOURCES['price']

            for source_idx, source in enumerate(sources):
                logger.debug(f"Trying source {source} for {symbol} ({source_idx + 1}/{len(sources)})")

                def fetch_from_source():
                    stock = Vnstock().stock(symbol=symbol, source=source)
                    return stock.quote.history(start=config.START_DATE, end=config.TODAY, interval='1D')

                df = self._retry_with_backoff(fetch_from_source, symbol)

                if df is not None and not df.empty:
                    # Validate before saving
                    is_valid, message = self.validator.validate_price_data(df, symbol)
                    if is_valid:
                        logger.info(f"✓ Successfully fetched price for {symbol} from {source}")
                        self._save_to_cache(df, file_path)
                        return df
                    else:
                        logger.warning(f"Price data validation failed for {symbol} from {source}: {message}")

                # Small delay before trying next source
                if source_idx < len(sources) - 1:
                    time.sleep(1)

            logger.error(f"Failed to fetch price for {symbol} from all sources: {sources}")
            return None

    def get_financial_report(self, symbol, report_type='BalanceSheet'):
        """
        Lấy báo cáo tài chính với retry logic
        """
        file_path = self._get_file_path(symbol, f"fin_{report_type}")
        cache_expiry = config.CACHE_EXPIRY['financial']

        # Check cache
        cached = self._load_from_cache(file_path, max_age_days=cache_expiry)
        if cached is not None:
            logger.debug(f"Using cached {report_type} for {symbol}")
            return cached

        try:
            df = None
            if self.use_legacy:
                # Legacy mode
                def fetch_legacy():
                    return vnstock.financial_report(
                        symbol=symbol,
                        report_type=report_type,
                        frequency='Quarterly'
                    )

                df = self._retry_with_backoff(fetch_legacy, symbol)
            else:
                # Modern mode - fallback through sources
                from vnstock import Vnstock
                sources = config.DATA_SOURCES['financial']

                for source in sources:
                    logger.debug(f"Trying {source} for {symbol} {report_type}")

                    def fetch_from_source():
                        stock = Vnstock().stock(symbol=symbol, source=source)

                        if report_type == 'BalanceSheet':
                            return stock.finance.balance_sheet(period='quarter', lang='vi')
                        elif report_type == 'IncomeStatement':
                            return stock.finance.income_statement(period='quarter', lang='vi')
                        elif report_type == 'CashFlow':
                            return stock.finance.cash_flow(period='quarter', lang='vi')
                        else:
                            return None

                    df = self._retry_with_backoff(fetch_from_source, symbol)

                    if df is not None and not df.empty:
                        # Validate before saving
                        is_valid, message = self.validator.validate_financial_data(df, symbol, report_type)
                        if is_valid:
                            logger.info(f"✓ Successfully fetched {report_type} for {symbol} from {source}")
                            self._save_to_cache(df, file_path)
                            return df
                        else:
                            logger.warning(f"{report_type} validation failed for {symbol} from {source}: {message}")

                    time.sleep(1)  # Delay before next source

            if df is not None and not df.empty:
                self._save_to_cache(df, file_path)
                return df

        except Exception as e:
            logger.error(f"Unexpected error fetching {report_type} for {symbol}: {e}")

        return None

    def run_ingestion(self, symbols):
        """
        Run full ingestion pipeline for list of symbols
        """
        logger.info(f"Starting data ingestion for {len(symbols)} symbols")
        logger.info(f"Data will be saved to: {self.data_dir}")
        logger.info("Note: This process may take time due to rate limiting")

        results = []
        success_count = 0
        partial_count = 0
        fail_count = 0

        for idx, symbol in enumerate(symbols):
            logger.info(f"[{idx+1}/{len(symbols)}] Processing {symbol}...")

            # Random sleep to avoid rate limiting
            sleep_time = random.uniform(
                config.RATE_LIMIT['request_delay_min'],
                config.RATE_LIMIT['request_delay_max']
            )
            time.sleep(sleep_time)

            # 1. Fetch price data (most important)
            price = self.get_price_data(symbol)

            # 2. Fetch financial data (only if price is OK to save requests)
            bs = None
            inc = None
            if price is not None:
                time.sleep(random.uniform(1, 2))
                bs = self.get_financial_report(symbol, 'BalanceSheet')

                if bs is not None:
                    time.sleep(random.uniform(1, 2))
                    inc = self.get_financial_report(symbol, 'IncomeStatement')

            # Determine status
            if price is None:
                status = "FAILED"
                fail_count += 1
                logger.error(f"✗ {symbol}: NO PRICE DATA")
            elif bs is None:
                status = "PARTIAL"
                partial_count += 1
                logger.warning(f"⚠ {symbol}: PRICE ONLY (missing financial data)")
            else:
                status = "SUCCESS"
                success_count += 1
                logger.info(f"✓ {symbol}: COMPLETE")

            results.append({
                'Symbol': symbol,
                'Status': status,
                'Has_Price': price is not None,
                'Has_Balance': bs is not None,
                'Has_Income': inc is not None
            })

        # Summary
        logger.info("=" * 60)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total: {len(symbols)} symbols")
        logger.info(f"Success: {success_count} ({success_count/len(symbols)*100:.1f}%)")
        logger.info(f"Partial: {partial_count} ({partial_count/len(symbols)*100:.1f}%)")
        logger.info(f"Failed: {fail_count} ({fail_count/len(symbols)*100:.1f}%)")
        logger.info("=" * 60)

        return pd.DataFrame(results)
