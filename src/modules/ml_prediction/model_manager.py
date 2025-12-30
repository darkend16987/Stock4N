"""
Model Manager - Quản lý ML models
Lưu/load models, versioning, và metadata
"""
import joblib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class ModelManager:
    """
    Quản lý trained models và metadata
    """

    def __init__(self, models_dir=None):
        if models_dir is None:
            self.models_dir = os.path.join(config.BASE_DIR, 'data', 'ml_models')
        else:
            self.models_dir = models_dir

        os.makedirs(self.models_dir, exist_ok=True)

    def save_model(self, model, model_name='trend_classifier', version=None, metadata=None):
        """
        Lưu trained model

        Args:
            model: Trained model object
            model_name: Model name
            version: Version string (default: timestamp)
            metadata: Dict of additional metadata

        Returns:
            str: Path to saved model
        """
        if version is None:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create version directory
        version_dir = os.path.join(self.models_dir, model_name, version)
        os.makedirs(version_dir, exist_ok=True)

        # Save model
        model_file = os.path.join(version_dir, 'model.pkl')
        joblib.dump(model, model_file)

        # Save metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            'model_name': model_name,
            'version': version,
            'saved_at': datetime.now().isoformat(),
            'model_type': getattr(model, 'model_type', 'unknown'),
            'feature_names': getattr(model, 'feature_names', []),
            'metrics': getattr(model, 'metrics', {})
        })

        metadata_file = os.path.join(version_dir, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save feature importance if available
        if hasattr(model, 'feature_importance') and model.feature_importance is not None:
            importance_file = os.path.join(version_dir, 'feature_importance.csv')
            model.feature_importance.to_csv(importance_file, index=False)

        # Create 'latest' symlink (on Windows, copy instead)
        latest_dir = os.path.join(self.models_dir, model_name, 'latest')
        if os.path.exists(latest_dir):
            import shutil
            shutil.rmtree(latest_dir)

        # Copy instead of symlink for Windows compatibility
        import shutil
        shutil.copytree(version_dir, latest_dir)

        logger.info(f"Saved model to {version_dir}")
        return version_dir

    def load_model(self, model_name='trend_classifier', version='latest'):
        """
        Load trained model

        Args:
            model_name: Model name
            version: Version to load (default: 'latest')

        Returns:
            model: Loaded model object
        """
        model_dir = os.path.join(self.models_dir, model_name, version)

        if not os.path.exists(model_dir):
            logger.error(f"Model not found: {model_dir}")
            return None

        model_file = os.path.join(model_dir, 'model.pkl')

        if not os.path.exists(model_file):
            logger.error(f"Model file not found: {model_file}")
            return None

        model = joblib.load(model_file)

        logger.info(f"Loaded model from {model_dir}")
        return model

    def load_metadata(self, model_name='trend_classifier', version='latest'):
        """
        Load model metadata

        Args:
            model_name: Model name
            version: Version

        Returns:
            dict: Metadata
        """
        model_dir = os.path.join(self.models_dir, model_name, version)
        metadata_file = os.path.join(model_dir, 'metadata.json')

        if not os.path.exists(metadata_file):
            logger.warning(f"Metadata not found: {metadata_file}")
            return None

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        return metadata

    def list_versions(self, model_name='trend_classifier'):
        """
        List all saved versions

        Args:
            model_name: Model name

        Returns:
            list: [(version, saved_at, accuracy), ...]
        """
        model_base = os.path.join(self.models_dir, model_name)

        if not os.path.exists(model_base):
            return []

        versions = []
        for item in os.listdir(model_base):
            if item == 'latest':
                continue

            version_dir = os.path.join(model_base, item)
            if os.path.isdir(version_dir):
                metadata = self.load_metadata(model_name, item)
                if metadata:
                    test_acc = metadata.get('metrics', {}).get('test_accuracy', 'N/A')
                    versions.append((
                        item,
                        metadata.get('saved_at', 'N/A'),
                        test_acc
                    ))

        # Sort by version (timestamp)
        versions.sort(reverse=True)

        return versions

    def compare_versions(self, model_name='trend_classifier', versions=None):
        """
        So sánh performance của các versions

        Args:
            model_name: Model name
            versions: List of versions to compare (default: all)

        Returns:
            DataFrame: Comparison table
        """
        import pandas as pd

        if versions is None:
            versions = [v[0] for v in self.list_versions(model_name)]

        if not versions:
            logger.warning("No versions to compare")
            return None

        comparison_data = []

        for version in versions:
            metadata = self.load_metadata(model_name, version)
            if metadata:
                metrics = metadata.get('metrics', {})

                comparison_data.append({
                    'version': version,
                    'saved_at': metadata.get('saved_at', 'N/A'),
                    'train_accuracy': metrics.get('train_accuracy', 'N/A'),
                    'test_accuracy': metrics.get('test_accuracy', 'N/A'),
                    'train_samples': metrics.get('train_samples', 'N/A'),
                    'test_samples': metrics.get('test_samples', 'N/A'),
                    'n_features': metrics.get('n_features', 'N/A')
                })

        df = pd.DataFrame(comparison_data)

        return df

    def delete_version(self, model_name='trend_classifier', version=None):
        """
        Xóa một version

        Args:
            model_name: Model name
            version: Version to delete

        Returns:
            bool: Success status
        """
        if version == 'latest':
            logger.error("Cannot delete 'latest' version")
            return False

        version_dir = os.path.join(self.models_dir, model_name, version)

        if not os.path.exists(version_dir):
            logger.error(f"Version not found: {version}")
            return False

        import shutil
        shutil.rmtree(version_dir)

        logger.info(f"Deleted version: {version}")
        return True

    def export_model(self, model_name='trend_classifier', version='latest', output_file=None):
        """
        Export model cùng metadata sang file duy nhất

        Args:
            model_name: Model name
            version: Version
            output_file: Output path (default: models_dir/model_name_version.zip)

        Returns:
            str: Path to exported file
        """
        import shutil

        version_dir = os.path.join(self.models_dir, model_name, version)

        if not os.path.exists(version_dir):
            logger.error(f"Model version not found: {version}")
            return None

        if output_file is None:
            output_file = os.path.join(self.models_dir, f"{model_name}_{version}")

        # Create zip archive
        shutil.make_archive(output_file, 'zip', version_dir)

        logger.info(f"Exported model to {output_file}.zip")
        return f"{output_file}.zip"

    def import_model(self, zip_file, model_name='trend_classifier', version=None):
        """
        Import model từ exported zip file

        Args:
            zip_file: Path to zip file
            model_name: Model name
            version: Version name (default: from metadata)

        Returns:
            bool: Success status
        """
        import zipfile
        import tempfile
        import shutil

        if not os.path.exists(zip_file):
            logger.error(f"Zip file not found: {zip_file}")
            return False

        # Extract to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Read metadata to get version
            metadata_file = os.path.join(temp_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    if version is None:
                        version = metadata.get('version', 'imported')

            # Copy to models directory
            version_dir = os.path.join(self.models_dir, model_name, version)
            if os.path.exists(version_dir):
                logger.warning(f"Version already exists: {version}")
                return False

            shutil.copytree(temp_dir, version_dir)

        logger.info(f"Imported model to {version_dir}")
        return True

    def get_best_model(self, model_name='trend_classifier', metric='test_accuracy'):
        """
        Lấy model có performance tốt nhất

        Args:
            model_name: Model name
            metric: Metric to optimize ('test_accuracy', 'train_accuracy')

        Returns:
            tuple: (version, model, metadata)
        """
        versions = self.list_versions(model_name)

        if not versions:
            logger.warning("No models found")
            return None

        # Find best version by metric
        best_version = None
        best_score = -1

        for version, saved_at, test_acc in versions:
            metadata = self.load_metadata(model_name, version)
            if metadata:
                score = metadata.get('metrics', {}).get(metric, -1)
                if score > best_score:
                    best_score = score
                    best_version = version

        if best_version:
            model = self.load_model(model_name, best_version)
            metadata = self.load_metadata(model_name, best_version)

            logger.info(f"Best model: {best_version} ({metric}={best_score:.3f})")
            return (best_version, model, metadata)

        return None

    def get_summary(self):
        """
        Summary of all saved models

        Returns:
            str: Formatted summary
        """
        summary = "=== ML MODELS SUMMARY ===\n\n"

        # List all model types
        if not os.path.exists(self.models_dir):
            return summary + "No models directory found"

        model_types = [d for d in os.listdir(self.models_dir) if os.path.isdir(os.path.join(self.models_dir, d))]

        for model_name in model_types:
            summary += f"Model: {model_name}\n"

            versions = self.list_versions(model_name)
            summary += f"  Versions: {len(versions)}\n"

            if versions:
                # Latest version info
                latest_metadata = self.load_metadata(model_name, 'latest')
                if latest_metadata:
                    metrics = latest_metadata.get('metrics', {})
                    summary += f"  Latest Test Accuracy: {metrics.get('test_accuracy', 'N/A')}\n"
                    summary += f"  Saved At: {latest_metadata.get('saved_at', 'N/A')}\n"

            summary += "\n"

        summary += "======================="

        return summary
