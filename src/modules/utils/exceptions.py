"""
Custom Exception Classes for Stock4N
"""


class Stock4NException(Exception):
    """Base exception for Stock4N application"""
    pass


# Data Ingestion Exceptions
class DataIngestionException(Stock4NException):
    """Base exception for data ingestion errors"""
    pass


class APIRateLimitException(DataIngestionException):
    """Raised when API rate limit is hit"""
    pass


class APISourceUnavailableException(DataIngestionException):
    """Raised when all API sources fail"""
    pass


class InvalidSymbolException(DataIngestionException):
    """Raised when symbol format is invalid"""
    pass


# Data Processing Exceptions
class DataProcessingException(Stock4NException):
    """Base exception for data processing errors"""
    pass


class InsufficientDataException(DataProcessingException):
    """Raised when not enough data to perform calculation"""
    pass


class InvalidDataException(DataProcessingException):
    """Raised when data format is invalid or corrupted"""
    pass


class MissingColumnException(DataProcessingException):
    """Raised when required column is missing from DataFrame"""
    pass


# Analysis Exceptions
class AnalysisException(Stock4NException):
    """Base exception for analysis errors"""
    pass


class ScoringException(AnalysisException):
    """Raised when scoring calculation fails"""
    pass


# Portfolio Exceptions
class PortfolioException(Stock4NException):
    """Base exception for portfolio management errors"""
    pass


class InsufficientCapitalException(PortfolioException):
    """Raised when capital is insufficient for allocation"""
    pass


class NoValidPositionException(PortfolioException):
    """Raised when no valid positions can be created"""
    pass


# Validation Exceptions
class ValidationException(Stock4NException):
    """Base exception for validation errors"""
    pass


class DataQualityException(ValidationException):
    """Raised when data quality is below threshold"""
    pass


class ConfigurationException(Stock4NException):
    """Raised when configuration is invalid"""
    pass
