"""
Trend Classifier - Phân loại xu hướng bằng ML
Sử dụng Random Forest để dự đoán trend (UP/NEUTRAL/DOWN)
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class TrendClassifier:
    """
    ML Model để phân loại xu hướng giá
    """

    def __init__(self, model_type='random_forest'):
        """
        Args:
            model_type: 'random_forest' or 'gradient_boosting'
        """
        self.model_type = model_type
        self.model = None
        self.feature_names = None
        self.feature_importance = None
        self.metrics = {}

        self._initialize_model()

    def _initialize_model(self):
        """Initialize ML model"""
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model_type: {self.model_type}")

        logger.info(f"Initialized {self.model_type} classifier")

    def prepare_data(self, df, feature_names):
        """
        Chuẩn bị data cho training

        Args:
            df: DataFrame with features and target
            feature_names: List of feature column names

        Returns:
            X, y: Features and target
        """
        # Ensure all features exist
        missing_features = [f for f in feature_names if f not in df.columns]
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
            feature_names = [f for f in feature_names if f in df.columns]

        X = df[feature_names].values
        y = df['target'].values

        self.feature_names = feature_names

        return X, y

    def train(self, df, feature_names, test_size=0.2):
        """
        Train model

        Args:
            df: DataFrame with features and target
            feature_names: List of feature columns
            test_size: Test set ratio

        Returns:
            dict: Training metrics
        """
        logger.info("Training model...")

        # Prepare data
        X, y = self.prepare_data(df, feature_names)

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        logger.info(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Train
        self.model.fit(X_train, y_train)

        # Predict
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        # Metrics
        train_acc = accuracy_score(y_train, y_pred_train)
        test_acc = accuracy_score(y_test, y_pred_test)

        logger.info(f"Train Accuracy: {train_acc:.3f}")
        logger.info(f"Test Accuracy: {test_acc:.3f}")

        # Classification report
        logger.info("\nTest Set Classification Report:")
        report = classification_report(y_test, y_pred_test,
                                       target_names=['DOWN', 'NEUTRAL', 'UP'],
                                       output_dict=True)
        logger.info(classification_report(y_test, y_pred_test,
                                          target_names=['DOWN', 'NEUTRAL', 'UP']))

        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)

            logger.info("\nTop 10 Important Features:")
            for idx, row in self.feature_importance.head(10).iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        # Save metrics
        self.metrics = {
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'classification_report': report,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'n_features': len(self.feature_names)
        }

        return self.metrics

    def train_multi_symbol(self, datasets, feature_names, test_size=0.2):
        """
        Train model trên nhiều symbols (pooled data)

        Args:
            datasets: dict {symbol: dataframe}
            feature_names: List of feature columns
            test_size: Test set ratio

        Returns:
            dict: Training metrics
        """
        logger.info(f"Training on {len(datasets)} symbols...")

        # Combine all datasets
        all_dfs = []
        for symbol, df in datasets.items():
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            all_dfs.append(df_copy)

        combined_df = pd.concat(all_dfs, ignore_index=True)

        logger.info(f"Combined dataset: {len(combined_df)} samples")

        # Train on combined data
        metrics = self.train(combined_df, feature_names, test_size)

        return metrics

    def predict(self, X):
        """
        Predict trend

        Args:
            X: Features (array or DataFrame)

        Returns:
            predictions: Array of predictions (-1, 0, 1)
        """
        if self.model is None:
            raise ValueError("Model not trained yet!")

        if isinstance(X, pd.DataFrame):
            X = X[self.feature_names].values

        predictions = self.model.predict(X)

        return predictions

    def predict_proba(self, X):
        """
        Predict probabilities for each class

        Args:
            X: Features

        Returns:
            probabilities: Array of shape (n_samples, 3)
                          [P(DOWN), P(NEUTRAL), P(UP)]
        """
        if self.model is None:
            raise ValueError("Model not trained yet!")

        if isinstance(X, pd.DataFrame):
            X = X[self.feature_names].values

        probabilities = self.model.predict_proba(X)

        return probabilities

    def predict_single(self, features):
        """
        Predict trend cho 1 sample

        Args:
            features: Series or dict of feature values

        Returns:
            dict: {
                'prediction': int,
                'prediction_label': str,
                'probabilities': dict,
                'confidence': float
            }
        """
        if isinstance(features, dict):
            features = pd.Series(features)

        # Ensure correct feature order
        X = features[self.feature_names].values.reshape(1, -1)

        # Predict
        pred = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)[0]

        # Labels
        labels = {-1: 'DOWN', 0: 'NEUTRAL', 1: 'UP'}
        pred_label = labels[pred]

        # Probabilities
        proba_dict = {
            'DOWN': proba[0],
            'NEUTRAL': proba[1],
            'UP': proba[2]
        }

        # Confidence (max probability)
        confidence = max(proba)

        result = {
            'prediction': int(pred),
            'prediction_label': pred_label,
            'probabilities': proba_dict,
            'confidence': float(confidence)
        }

        return result

    def evaluate_on_new_data(self, df, feature_names):
        """
        Evaluate model trên data mới

        Args:
            df: DataFrame with features and target

        Returns:
            dict: Evaluation metrics
        """
        logger.info("Evaluating on new data...")

        X, y = self.prepare_data(df, feature_names)

        y_pred = self.model.predict(X)

        accuracy = accuracy_score(y, y_pred)

        report = classification_report(y, y_pred,
                                       target_names=['DOWN', 'NEUTRAL', 'UP'],
                                       output_dict=True)

        logger.info(f"Accuracy: {accuracy:.3f}")
        logger.info(classification_report(y, y_pred,
                                          target_names=['DOWN', 'NEUTRAL', 'UP']))

        return {
            'accuracy': accuracy,
            'classification_report': report,
            'n_samples': len(X)
        }

    def get_feature_importance(self, top_n=20):
        """
        Lấy feature importance

        Args:
            top_n: Number of top features to return

        Returns:
            DataFrame: Feature importance
        """
        if self.feature_importance is None:
            logger.warning("Feature importance not available")
            return None

        return self.feature_importance.head(top_n)

    def cross_validate(self, df, feature_names, cv=5):
        """
        Cross validation

        Args:
            df: DataFrame
            feature_names: Feature columns
            cv: Number of folds

        Returns:
            dict: CV scores
        """
        logger.info(f"Running {cv}-fold cross validation...")

        X, y = self.prepare_data(df, feature_names)

        scores = cross_val_score(self.model, X, y, cv=cv, scoring='accuracy')

        logger.info(f"CV Scores: {scores}")
        logger.info(f"Mean: {scores.mean():.3f} (+/- {scores.std():.3f})")

        return {
            'scores': scores.tolist(),
            'mean': scores.mean(),
            'std': scores.std()
        }

    def get_model_summary(self):
        """
        Tạo summary của model

        Returns:
            str: Formatted summary
        """
        if self.metrics is None or len(self.metrics) == 0:
            return "Model not trained yet"

        summary = f"""
=== TREND CLASSIFIER SUMMARY ===

Model Type: {self.model_type}

Training Data:
  Train Samples: {self.metrics.get('train_samples', 'N/A')}
  Test Samples: {self.metrics.get('test_samples', 'N/A')}
  Features: {self.metrics.get('n_features', 'N/A')}

Performance:
  Train Accuracy: {self.metrics.get('train_accuracy', 0):.3f}
  Test Accuracy: {self.metrics.get('test_accuracy', 0):.3f}

Per-Class Performance (Test Set):
"""
        report = self.metrics.get('classification_report', {})
        for label in ['DOWN', 'NEUTRAL', 'UP']:
            if label in report:
                metrics_dict = report[label]
                summary += f"\n  {label}:"
                summary += f"\n    Precision: {metrics_dict.get('precision', 0):.3f}"
                summary += f"\n    Recall: {metrics_dict.get('recall', 0):.3f}"
                summary += f"\n    F1-Score: {metrics_dict.get('f1-score', 0):.3f}"

        summary += "\n\nTop 5 Important Features:"
        if self.feature_importance is not None:
            for idx, row in self.feature_importance.head(5).iterrows():
                summary += f"\n  {row['feature']}: {row['importance']:.4f}"

        summary += "\n\n================================="

        return summary
