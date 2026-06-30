"""
Project utilities for data analysis and journalism workflows.

Importing this package also puts the project root on sys.path, so `import config`
works from notebooks regardless of the kernel's working directory.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from .data_utils import (
    quick_info,
    plot_distributions,
    correlation_analysis,
    detect_outliers,
    clean_column_names,
    memory_optimization,
    create_date_features,
    categorical_analysis,
)

from .journalism_utils import (
    quick_export_for_web,
    create_story_charts,
    data_fact_check,
    quick_summary_table,
    compare_periods,
)

__all__ = [
    # Data analysis utilities
    'quick_info',
    'plot_distributions',
    'correlation_analysis',
    'detect_outliers',
    'clean_column_names',
    'memory_optimization',
    'create_date_features',
    'categorical_analysis',
    # Journalism utilities
    'quick_export_for_web',
    'create_story_charts',
    'data_fact_check',
    'quick_summary_table',
    'compare_periods',
]
