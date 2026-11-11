"""
config module for Arachudar Tamil News Automation.
"""

from config.sources import (
    TAMIL_NEWS_SOURCES,
    VALID_CATEGORIES,
    VALID_SUBCATEGORIES,
    CATEGORY_KEYWORDS_MAP,
    SUBCATEGORY_KEYWORDS_MAP,
    DEFAULT_USER_AGENT,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    SourceConfig,
    get_source_config,
    map_category,
    map_subcategory,
)

__all__ = [
    "TAMIL_NEWS_SOURCES",
    "VALID_CATEGORIES",
    "VALID_SUBCATEGORIES",
    "CATEGORY_KEYWORDS_MAP",
    "SUBCATEGORY_KEYWORDS_MAP",
    "DEFAULT_USER_AGENT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "SourceConfig",
    "get_source_config",
    "map_category",
    "map_subcategory",
]
