"""
Zentrales Logging System für alle Module
Konsistente Log-Formatierung, Levels, und Output
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class Logger:
    """
    Zentrales Logging System
    
    Features:
    - Konsistente Log-Formatierung
    - Log Levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - File und Console Output
    - Timestamp und Module Tracking
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialisiere Logger
        
        Args:
            name: Logger Name (Module Name)
            level: Log Level (default: INFO)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Verhindere doppelte Handler
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup Console und File Handler"""
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File Handler (optional)
        try:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / f'{datetime.now().strftime("%Y%m%d")}.log'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            # File Logging ist optional
            pass
    
    def debug(self, message: str, **kwargs):
        """Log Debug Message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log Info Message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log Warning Message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log Error Message"""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log Critical Message"""
        self.logger.critical(message, extra=kwargs)


# Beispiel-Usage
if __name__ == "__main__":
    logger = Logger("test")
    logger.info("Test message")
    logger.warning("Warning message")
    logger.error("Error message")