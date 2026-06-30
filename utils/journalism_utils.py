"""
Data Journalism Utilities

Specialized functions for fast-paced journalism workflows.
"""

import pandas as pd
import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import sys
import os

# Try to import config for proper path resolution
try:
    # Add parent directory to path to import config
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    import config
    PROCESSED_DATA_DIR = config.PROCESSED_DATA_DIR
    PROJECT_ROOT = config.PROJECT_ROOT
except ImportError:
    # Fallback if config not available (shouldn't happen in normal use)
    PROJECT_ROOT = Path.cwd()
    PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def quick_export_for_web(df: pd.DataFrame, filename: str, 
                        format_type: str = 'csv') -> str:
    """
    Quickly export data for web publishing or sharing.
    
    Args:
        df: pandas DataFrame to export
        filename: Output filename (without extension)
        format_type: 'csv', 'json', 'html' or 'excel'
        
    Returns:
        Path to the exported file
    """
    data_dir = PROCESSED_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    
    if format_type == 'csv':
        filepath = data_dir / f"{filename}.csv"
        df.to_csv(filepath, index=False)
    elif format_type == 'json':
        filepath = data_dir / f"{filename}.json"
        df.to_json(filepath, orient='records', indent=2)
    elif format_type == 'html':
        filepath = data_dir / f"{filename}.html"
        df.to_html(filepath, index=False, table_id="data-table", 
                  classes="table table-striped")
    elif format_type == 'excel':
        filepath = data_dir / f"{filename}.xlsx"
        df.to_excel(filepath, index=False)
    else:
        raise ValueError("format_type must be 'csv', 'json', 'html', or 'excel'")
    
    print(f"✅ Data exported to: {filepath}")
    return str(filepath)


def create_story_charts(df: pd.DataFrame, column: str, 
                       chart_type: str = 'auto', 
                       title: Optional[str] = None,
                       save_filename: Optional[str] = None) -> None:
    """
    Generate publication-ready charts quickly for journalism.
    
    Args:
        df: pandas DataFrame
        column: Column to visualize
        chart_type: 'auto', 'bar', 'line', 'histogram', 'pie'
        title: Chart title (auto-generated if None)
        save_filename: Save chart as PNG (optional)
    """
    if plt is None:
        raise ImportError(
            "matplotlib is required for create_story_charts. Install the visualization extras via"
            " `uv sync --extra viz` before using this helper."
        )

    plt.style.use('seaborn-v0_8')  # Clean, professional style
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if title is None:
        title = f"Analysis of {column.replace('_', ' ').title()}"
    
    # Auto-detect chart type based on data
    if chart_type == 'auto':
        if df[column].dtype in ['object', 'category']:
            chart_type = 'bar'
        elif pd.api.types.is_numeric_dtype(df[column]):
            if df[column].nunique() < 20:
                chart_type = 'bar'
            else:
                chart_type = 'histogram'
    
    # Create appropriate chart
    if chart_type == 'bar':
        value_counts = df[column].value_counts().head(10)
        bars = ax.bar(range(len(value_counts)), value_counts.values.tolist())
        ax.set_xticks(range(len(value_counts)))
        ax.set_xticklabels(value_counts.index, rotation=45, ha='right')
        ax.set_ylabel('Count')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom')
    
    elif chart_type == 'line':
        if df.index.dtype == 'datetime64[ns]' or 'date' in column.lower():
            df.plot(y=column, ax=ax, linewidth=2)
        else:
            ax.plot(df.index, df[column], linewidth=2)
        ax.set_ylabel(column.replace('_', ' ').title())
    
    elif chart_type == 'histogram':
        ax.hist(df[column].dropna(), bins=30, alpha=0.7, edgecolor='black')
        ax.set_xlabel(column.replace('_', ' ').title())
        ax.set_ylabel('Frequency')
    
    elif chart_type == 'pie':
        value_counts = df[column].value_counts().head(8)
        ax.pie(value_counts.values.tolist(), labels=value_counts.index.tolist(), autopct='%1.1f%%')
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    
    if save_filename:
        # Save charts in the current working directory (typically notebooks/)
        charts_dir = Path.cwd()
        chart_path = charts_dir / f"{save_filename}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        print(f"📊 Chart saved as: {chart_path}")
    
    plt.show()


def data_fact_check(df: pd.DataFrame, column: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick data validation and fact-checking for journalism.
    
    Args:
        df: pandas DataFrame
        column: Specific column to check (if None, checks entire DataFrame)
        
    Returns:
        Dictionary with validation results
    """
    results = {
        'timestamp': pd.Timestamp.now(),
        'total_rows': len(df),
        'total_columns': len(df.columns)
    }
    
    if column:
        # Single column analysis
        col_data = df[column]
        results[f'{column}_stats'] = {
            'missing_values': col_data.isnull().sum(),
            'missing_percentage': (col_data.isnull().sum() / len(col_data)) * 100,
            'unique_values': col_data.nunique(),
            'data_type': str(col_data.dtype)
        }
        
        if pd.api.types.is_numeric_dtype(col_data):
            results[f'{column}_stats'].update({
                'min': col_data.min(),
                'max': col_data.max(),
                'mean': col_data.mean(),
                'median': col_data.median(),
                'zeros': (col_data == 0).sum(),
                'negatives': (col_data < 0).sum() if col_data.min() < 0 else 0
            })
    else:
        # Overall DataFrame analysis
        results['missing_data'] = {
            'columns_with_missing': df.columns[df.isnull().any()].tolist(),
            'total_missing_values': df.isnull().sum().sum(),
            'missing_percentage': (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        }
        
        results['data_quality'] = {
            'duplicate_rows': df.duplicated().sum(),
            'empty_rows': df.isnull().all(axis=1).sum(),
            'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
            'text_columns': len(df.select_dtypes(include=['object']).columns),
            'date_columns': len(df.select_dtypes(include=['datetime']).columns)
        }
    
    # Print summary
    print("🔍 DATA FACT-CHECK SUMMARY")
    print("=" * 40)
    if column:
        stats = results[f'{column}_stats']
        print(f"Column: {column}")
        print(f"Missing values: {stats['missing_values']} ({stats['missing_percentage']:.1f}%)")
        print(f"Unique values: {stats['unique_values']}")
        if 'min' in stats:
            print(f"Range: {stats['min']} to {stats['max']}")
            print(f"Mean: {stats['mean']:.2f}, Median: {stats['median']:.2f}")
    else:
        print(f"Total records: {results['total_rows']:,}")
        print(f"Missing data: {results['missing_data']['total_missing_values']:,} values ({results['missing_data']['missing_percentage']:.1f}%)")
        print(f"Duplicate rows: {results['data_quality']['duplicate_rows']:,}")
        if results['missing_data']['columns_with_missing']:
            print(f"Columns with missing data: {', '.join(results['missing_data']['columns_with_missing'])}")
    
    return results


def quick_summary_table(df: pd.DataFrame, group_by: str, 
                       aggregate_cols: List[str], 
                       agg_func: str = 'sum') -> pd.DataFrame:
    """
    Create quick summary tables for journalism (like "totals by state").
    
    Args:
        df: pandas DataFrame
        group_by: Column to group by
        aggregate_cols: Columns to aggregate
        agg_func: 'sum', 'mean', 'count', 'max', 'min'
        
    Returns:
        Summarized DataFrame
    """
    summary = df.groupby(group_by)[aggregate_cols].agg(agg_func)
    
    # Sort by first aggregate column (descending)
    summary = summary.sort_values(summary.columns[0], ascending=False)
    
    print(f"📊 Summary: {agg_func.title()} of {', '.join(aggregate_cols)} by {group_by}")
    print("-" * 60)
    print(summary.head(10))
    
    return summary


def compare_periods(df: pd.DataFrame, date_col: str, value_col: str,
                   period1: str, period2: str) -> Dict[str, Any]:
    """
    Compare a metric across two date windows.

    Args:
        df: pandas DataFrame with date column
        date_col: Name of date column
        value_col: Name of value column to compare
        period1: Start of the first window (YYYY-MM-DD)
        period2: Start of the second window / end of the first (YYYY-MM-DD)

    Returns:
        Comparison statistics dict with totals, means, counts, and percent change

    Example:
        compare_periods(df, 'date', 'homicides', '2022-01-01', '2023-01-01')
        # compares Jan–Dec 2022 vs Jan 2023 onward
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    p1 = pd.to_datetime(period1)
    p2 = pd.to_datetime(period2)

    window1 = df[(df[date_col] >= p1) & (df[date_col] < p2)][value_col]
    window2 = df[df[date_col] >= p2][value_col]

    comparison = {
        'period1_total': window1.sum(),
        'period2_total': window2.sum(),
        'period1_mean': window1.mean(),
        'period2_mean': window2.mean(),
        'period1_count': len(window1),
        'period2_count': len(window2),
    }

    comparison['total_change'] = comparison['period2_total'] - comparison['period1_total']
    comparison['mean_change'] = comparison['period2_mean'] - comparison['period1_mean']
    if comparison['period1_total']:
        comparison['percent_change'] = ((comparison['period2_total'] / comparison['period1_total']) - 1) * 100
    else:
        comparison['percent_change'] = float('nan')

    print(f"📈 PERIOD COMPARISON: {value_col}")
    print("=" * 50)
    print(f"{period1}–{period2}: {comparison['period1_total']:,.0f} total, {comparison['period1_mean']:.2f} avg ({comparison['period1_count']:,} rows)")
    print(f"{period2} onward:   {comparison['period2_total']:,.0f} total, {comparison['period2_mean']:.2f} avg ({comparison['period2_count']:,} rows)")
    print(f"Change: {comparison['total_change']:+,.0f} ({comparison['percent_change']:+.1f}%)")

    return comparison
