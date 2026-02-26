import pandas as pd
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class DataExporter:
    """
    Module chuyển đổi dữ liệu CSV sang JSON để phục vụ Web Frontend
    """
    def __init__(self, processed_dir=config.PROCESSED_DIR, raw_dir=config.RAW_DIR):
        self.processed_dir = processed_dir
        self.raw_dir = raw_dir
        self.export_dir = config.EXPORT_CONFIG['export_dir']
        self.chart_limit = config.EXPORT_CONFIG['chart_history_limit']

        os.makedirs(self.export_dir, exist_ok=True)
        logger.info(f"DataExporter initialized: Export to {self.export_dir}")

    def export_all(self):
        """Export all data to JSON format for web frontend"""
        logger.info("Starting data export to JSON...")

        data_store = {
            "last_updated": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            "analysis": [],
            "portfolio": [],
            "charts": {}
        }

        # 1. Export Analysis Report
        analysis_path = os.path.join(self.processed_dir, "analysis_report.csv")
        if os.path.exists(analysis_path):
            logger.info("Exporting analysis report...")
            df = pd.read_csv(analysis_path)
            data_store["analysis"] = df.to_dict(orient="records")
            logger.info(f"✓ Exported {len(df)} analysis records")
        else:
            logger.warning(f"Analysis report not found: {analysis_path}")

        # 2. Export Portfolio Recommendations
        portfolio_path = os.path.join(self.processed_dir, "portfolio_recommendation.csv")
        if os.path.exists(portfolio_path):
            logger.info("Exporting portfolio recommendations...")
            df = pd.read_csv(portfolio_path)
            data_store["portfolio"] = df.to_dict(orient="records")
            logger.info(f"✓ Exported {len(df)} portfolio positions")
        else:
            logger.warning(f"Portfolio recommendation not found: {portfolio_path}")

        # 3. Export Price History (Charts)
        if data_store["analysis"]:
            logger.info(f"Exporting price charts (last {self.chart_limit} days)...")
            symbols = [item['Symbol'] for item in data_store["analysis"]]
            chart_count = 0

            for symbol in symbols:
                price_path = os.path.join(self.raw_dir, f"{symbol}_price.csv")
                if os.path.exists(price_path):
                    try:
                        df = pd.read_csv(price_path)
                        # Only take recent history to reduce file size
                        df = df.tail(self.chart_limit)
                        data_store["charts"][symbol] = df.to_dict(orient="records")
                        chart_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to export chart for {symbol}: {e}")

            logger.info(f"✓ Exported {chart_count}/{len(symbols)} price charts")

        # 4. Add metadata
        data_store["metadata"] = {
            "total_symbols": len(data_store["analysis"]),
            "total_positions": len(data_store["portfolio"]),
            "chart_days": self.chart_limit,
            "export_timestamp": pd.Timestamp.now().isoformat()
        }

        # 5. Save to JSON
        output_file = os.path.join(self.export_dir, "db.json")
        try:
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(data_store, f, ensure_ascii=False, indent=2)

            file_size = os.path.getsize(output_file) / 1024  # KB

            logger.info("=" * 60)
            logger.info("EXPORT SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Output file: {output_file}")
            logger.info(f"File size: {file_size:.1f} KB")
            logger.info(f"Analysis records: {len(data_store['analysis'])}")
            logger.info(f"Portfolio positions: {len(data_store['portfolio'])}")
            logger.info(f"Price charts: {len(data_store['charts'])}")
            logger.info(f"Last updated: {data_store['last_updated']}")
            logger.info("=" * 60)
            logger.info("✓ Export completed successfully!")

        except Exception as e:
            logger.error(f"Failed to save JSON file: {e}")
            raise

        # 6. Upload to Cloud Storage (if in Cloud Run environment)
        if os.environ.get('K_SERVICE'):  # Cloud Run environment variable
            try:
                self.upload_to_cloud_storage(output_file)
            except Exception as e:
                logger.warning(f"Cloud Storage upload failed (continuing anyway): {e}")

    def upload_to_cloud_storage(self, local_file_path):
        """
        Upload db.json to Google Cloud Storage
        Only runs in Cloud Run environment
        """
        try:
            from google.cloud import storage
        except ImportError:
            logger.warning("google-cloud-storage not installed, skipping upload")
            return

        bucket_name = os.environ.get('BUCKET_NAME')
        if not bucket_name:
            logger.warning("BUCKET_NAME not set, skipping Cloud Storage upload")
            return

        logger.info("Uploading to Google Cloud Storage...")

        try:
            # Initialize client
            client = storage.Client()
            bucket = client.bucket(bucket_name)

            # Upload db.json
            blob = bucket.blob('db.json')
            blob.upload_from_filename(
                local_file_path,
                content_type='application/json'
            )

            # Set cache control and make public
            blob.cache_control = 'public, max-age=3600'  # 1 hour cache
            blob.patch()
            blob.make_public()

            public_url = blob.public_url

            logger.info("=" * 60)
            logger.info("CLOUD STORAGE UPLOAD")
            logger.info("=" * 60)
            logger.info(f"Bucket: gs://{bucket_name}")
            logger.info(f"File: db.json")
            logger.info(f"Public URL: {public_url}")
            logger.info("=" * 60)
            logger.info("✓ Cloud Storage upload completed!")

            return public_url

        except Exception as e:
            logger.error(f"Failed to upload to Cloud Storage: {e}")
            raise


if __name__ == "__main__":
    exporter = DataExporter()
    exporter.export_all()
