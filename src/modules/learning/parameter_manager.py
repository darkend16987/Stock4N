"""
Parameter Manager - Quản lý tham số đã học
Lưu/load các tham số tối ưu, patterns, và cấu hình
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class ParameterManager:
    """
    Quản lý parameters và learned data
    """

    def __init__(self, params_dir=None):
        if params_dir is None:
            self.params_dir = os.path.join(config.BASE_DIR, 'data', 'learned_params')
        else:
            self.params_dir = params_dir

        os.makedirs(self.params_dir, exist_ok=True)
        self.parameters = {}

    def save_weights(self, weights, version=None):
        """
        Lưu trọng số tối ưu

        Args:
            weights: dict {fund_weight, tech_weight, performance}
            version: Version name (default: timestamp)
        """
        if version is None:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')

        filename = f"weights_v{version}.json"
        filepath = os.path.join(self.params_dir, filename)

        data = {
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'weights': weights
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Also save as 'latest'
        latest_file = os.path.join(self.params_dir, 'weights_latest.json')
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved weights to {filepath}")
        return filepath

    def load_weights(self, version='latest'):
        """
        Load trọng số đã lưu

        Args:
            version: Version to load (default: 'latest')

        Returns:
            dict: {fund_weight, tech_weight, performance}
        """
        if version == 'latest':
            filename = 'weights_latest.json'
        else:
            filename = f"weights_v{version}.json"

        filepath = os.path.join(self.params_dir, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Weights file not found: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded weights from {filepath}")
        return data['weights']

    def save_patterns(self, patterns, version=None):
        """
        Lưu patterns đã phát hiện

        Args:
            patterns: dict {symbol: {seasonality, momentum, support_resistance}}
            version: Version name
        """
        if version is None:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')

        filename = f"patterns_v{version}.json"
        filepath = os.path.join(self.params_dir, filename)

        data = {
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'patterns': patterns
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Also save as 'latest'
        latest_file = os.path.join(self.params_dir, 'patterns_latest.json')
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved patterns to {filepath}")
        return filepath

    def load_patterns(self, version='latest'):
        """
        Load patterns đã lưu

        Args:
            version: Version to load (default: 'latest')

        Returns:
            dict: {symbol: {seasonality, momentum, support_resistance}}
        """
        if version == 'latest':
            filename = 'patterns_latest.json'
        else:
            filename = f"patterns_v{version}.json"

        filepath = os.path.join(self.params_dir, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Patterns file not found: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded patterns from {filepath}")
        return data['patterns']

    def save_strategy_config(self, config_dict, name='default'):
        """
        Lưu cấu hình chiến lược

        Args:
            config_dict: dict containing strategy parameters
            name: Config name
        """
        filename = f"strategy_config_{name}.json"
        filepath = os.path.join(self.params_dir, filename)

        data = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'config': config_dict
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved strategy config to {filepath}")
        return filepath

    def load_strategy_config(self, name='default'):
        """
        Load cấu hình chiến lược

        Args:
            name: Config name

        Returns:
            dict: Strategy configuration
        """
        filename = f"strategy_config_{name}.json"
        filepath = os.path.join(self.params_dir, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Strategy config not found: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded strategy config from {filepath}")
        return data['config']

    def list_versions(self, param_type='weights'):
        """
        Liệt kê tất cả versions đã lưu

        Args:
            param_type: 'weights' or 'patterns'

        Returns:
            list: [(version, timestamp, filepath), ...]
        """
        pattern = f"{param_type}_v*.json"
        files = sorted(Path(self.params_dir).glob(pattern), reverse=True)

        versions = []
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    versions.append((
                        data['version'],
                        data['timestamp'],
                        str(filepath)
                    ))
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")

        return versions

    def get_latest_version(self, param_type='weights'):
        """
        Lấy version mới nhất

        Args:
            param_type: 'weights' or 'patterns'

        Returns:
            str: Latest version name or None
        """
        versions = self.list_versions(param_type)
        if not versions:
            return None

        return versions[0][0]  # First item is latest

    def export_all_parameters(self, output_file=None):
        """
        Export tất cả parameters ra 1 file duy nhất

        Args:
            output_file: Output file path (default: params_dir/all_parameters.json)

        Returns:
            str: Output file path
        """
        if output_file is None:
            output_file = os.path.join(self.params_dir, 'all_parameters.json')

        weights = self.load_weights('latest')
        patterns = self.load_patterns('latest')
        strategy_config = self.load_strategy_config('default')

        data = {
            'export_timestamp': datetime.now().isoformat(),
            'weights': weights,
            'patterns': patterns,
            'strategy_config': strategy_config
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported all parameters to {output_file}")
        return output_file

    def import_all_parameters(self, input_file):
        """
        Import parameters từ file

        Args:
            input_file: Input file path

        Returns:
            bool: Success status
        """
        if not os.path.exists(input_file):
            logger.error(f"Import file not found: {input_file}")
            return False

        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Save each component
            if data.get('weights'):
                self.save_weights(data['weights'], version='imported')

            if data.get('patterns'):
                self.save_patterns(data['patterns'], version='imported')

            if data.get('strategy_config'):
                self.save_strategy_config(data['strategy_config'], name='imported')

            logger.info(f"Imported parameters from {input_file}")
            return True

        except Exception as e:
            logger.error(f"Error importing parameters: {e}")
            return False

    def get_summary(self):
        """
        Tạo summary của tất cả parameters đã lưu

        Returns:
            str: Formatted summary
        """
        summary = "=== LEARNED PARAMETERS SUMMARY ===\n\n"

        # Weights
        weights_versions = self.list_versions('weights')
        summary += f"Weights Versions: {len(weights_versions)}\n"
        if weights_versions:
            latest_weights = self.load_weights('latest')
            if latest_weights:
                summary += f"  Latest: Fund={latest_weights.get('fund_weight')}, "
                summary += f"Tech={latest_weights.get('tech_weight')}\n"

        # Patterns
        patterns_versions = self.list_versions('patterns')
        summary += f"\nPatterns Versions: {len(patterns_versions)}\n"
        if patterns_versions:
            latest_patterns = self.load_patterns('latest')
            if latest_patterns:
                summary += f"  Symbols with patterns: {len(latest_patterns)}\n"

        # Files in directory
        summary += f"\nFiles in {self.params_dir}:\n"
        for filepath in sorted(Path(self.params_dir).glob('*.json')):
            summary += f"  - {filepath.name}\n"

        summary += "\n==================================="

        return summary
