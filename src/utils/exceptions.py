# src/utils/exceptions.py

class ParserBaseError(Exception):
    """Base class for all parser-related errors."""
    pass

class ValidationError(ParserBaseError):
    """Raised when validation fails."""
    pass

class ParsingError(ParserBaseError):
    """Raised when parsing fails."""
    pass

class InitializationError(ParserBaseError):
    """Raised when initialization of a component fails."""
    pass
