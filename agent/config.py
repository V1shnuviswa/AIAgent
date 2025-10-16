"""
Configuration settings for the Mutual Funds Agent
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class AgentConfig:
    """Configuration for the Mutual Funds Agent"""
    
    # API Configurations
    PRODUCTION_API_BASE: str = os.getenv("PRODUCTION_API_BASE", "http://34.122.133.139:4000")
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
    MOONSHOT_MODEL: str = os.getenv("MOONSHOT_MODEL", "moonshotai/kimi-k2-instruct")
    MOONSHOT_BASE_URL: str = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    MOONSHOT_TEMPERATURE: float = float(os.getenv("MOONSHOT_TEMPERATURE", "0.0"))
    
    # Tavily API Configuration
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "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")
    
    # Request timeouts - Removed for full agentic processing
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "300"))  # 5 minutes for thorough processing  
    WEB_SCRAPE_TIMEOUT: int = int(os.getenv("WEB_SCRAPE_TIMEOUT", "180"))  # 3 minutes for web search
    
    # Agent behavior settings
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    MAX_WEB_SOURCES: int = 5
    
    # Intent detection settings
    INTENT_CONFIDENCE_THRESHOLD: float = 0.7
    
    def __post_init__(self):
        if not hasattr(self, "PREFERRED_DOMAINS") or self.PREFERRED_DOMAINS is None:
            self.PREFERRED_DOMAINS = [
                "sebi.gov.in", 
                "axismutualfund.com",
                "morningstar.in",
                "valueresearchonline.com"
            ]
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Create config from environment variables"""
        return cls()

# Default configuration instance
DEFAULT_CONFIG = AgentConfig()
