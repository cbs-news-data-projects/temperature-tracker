"""
Data Science Utilities

Common functions for data analysis and preprocessing.
"""

import pandas as pd
import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None

try:
    import seaborn as sns
except ImportError:  # pragma: no cover
    sns = None
from typing import List, Dict, Optional, Tuple


def quick_info(df: pd.DataFrame) -> None:
    """
    Display quick information about a DataFrame.
    
    Args:
        df: pandas DataFrame
    """
    print("=" * 50)
    print("DATASET OVERVIEW")
    print("=" * 50)
    print(f"Shape: {df.shape}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    print("\nColumn Types:")
    print(df.dtypes.value_counts())
    
    print("\n" + "=" * 50)
    print("MISSING VALUES")
    print("=" * 50)
    missing = df.isnull().sum()
    missing_pct = 100 * missing / len(df)
    missing_table = pd.DataFrame({
        'Missing_Count': missing,
        'Missing_Percentage': missing_pct
    })
    missing_table = missing_table[missing_table['Missing_Count'] > 0]
    if len(missing_table) > 0:
        print(missing_table.sort_values('Missing_Count', ascending=False))
    else:
        print("No missing values found!")
    
    print("\n" + "=" * 50)
    print("BASIC STATISTICS")
    print("=" * 50)
    print(df.describe())


def plot_distributions(df: pd.DataFrame, numeric_cols: Optional[List[str]] = None, 
                      figsize: Tuple[int, int] = (15, 10)) -> None:
    """
    Plot distributions of numeric columns.
    
    Args:
        df: pandas DataFrame
        numeric_cols: List of numeric columns to plot
        figsize: Figure size tuple
    """
    if plt is None:
        raise ImportError(
            "matplotlib is required for plot_distributions. Install the visualization extras via"
            " `uv sync --extra viz` before using this helper."
        )

    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    n_cols = min(3, len(numeric_cols))
    n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_rows == 1 and n_cols == 1:
        axes = [axes]
    elif n_rows == 1:
        axes = axes
    else:
        axes = axes.flatten()
    
    for i, col in enumerate(numeric_cols):
        if i < len(axes):
            df[col].hist(bins=30, ax=axes[i], alpha=0.7, edgecolor='black')
            axes[i].set_title(f'Distribution of {col}')
            axes[i].set_xlabel(col)
            axes[i].set_ylabel('Frequency')
    
    # Hide empty subplots
    for j in range(len(numeric_cols), len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    plt.show()


def correlation_analysis(df: pd.DataFrame, method: str = 'pearson', 
                        figsize: Tuple[int, int] = (10, 8)) -> pd.DataFrame:
    """
    Perform correlation analysis on numeric columns.
    
    Args:
        df: pandas DataFrame
        method: Correlation method ('pearson', 'spearman', 'kendall')
        figsize: Figure size tuple
        
    Returns:
        Correlation matrix
    """
    if plt is None or sns is None:
        raise ImportError(
            "matplotlib and seaborn are required for correlation_analysis. Install the visualization extras"
            " via `uv sync --extra viz` before using this helper."
        )

    numeric_df = df.select_dtypes(include=[np.number])
    corr_matrix = numeric_df.corr(method=method)
    
    plt.figure(figsize=figsize)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='coolwarm', 
                center=0, square=True, fmt='.2f')
    plt.title(f'{method.capitalize()} Correlation Matrix')
    plt.tight_layout()
    plt.show()
    
    return corr_matrix


def detect_outliers(df: pd.DataFrame, columns: Optional[List[str]] = None,
                   method: str = 'iqr') -> Dict[str, List[int]]:
    """
    Detect outliers using IQR or Z-score method.
    
    Args:
        df: pandas DataFrame
        columns: List of columns to check
        method: 'iqr' or 'zscore'
        
    Returns:
        Dictionary with column names as keys and outlier indices as values
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    outliers = {}
    
    for col in columns:
        if method == 'iqr':
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outlier_indices = df[(df[col] < lower_bound) | (df[col] > upper_bound)].index.tolist()
        
        elif method == 'zscore':
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            outlier_indices = df[z_scores > 3].index.tolist()
        
        outliers[col] = outlier_indices
    
    return outliers


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names by removing special characters and spaces.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        DataFrame with cleaned column names
    """
    df_cleaned = df.copy()
    df_cleaned.columns = (df_cleaned.columns
                         .str.strip()
                         .str.lower()
                         .str.replace(' ', '_')
                         .str.replace('[^a-zA-Z0-9_]', '', regex=True))
    return df_cleaned


def memory_optimization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage by converting to optimal dtypes.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        Memory optimized DataFrame
    """
    df_optimized = df.copy()
    
    for col in df_optimized.columns:
        col_type = df_optimized[col].dtype
        
        if col_type != 'object':
            c_min = df_optimized[col].min()
            c_max = df_optimized[col].max()
            
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df_optimized[col] = df_optimized[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df_optimized[col] = df_optimized[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df_optimized[col] = df_optimized[col].astype(np.int32)
                    
            elif str(col_type)[:5] == 'float':
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df_optimized[col] = df_optimized[col].astype(np.float32)
    
    return df_optimized


def create_date_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Create date-based features from a datetime column.
    
    Args:
        df: pandas DataFrame
        date_col: Name of the datetime column
        
    Returns:
        DataFrame with additional date features
    """
    df_with_dates = df.copy()
    df_with_dates[date_col] = pd.to_datetime(df_with_dates[date_col])
    
    df_with_dates[f'{date_col}_year'] = df_with_dates[date_col].dt.year
    df_with_dates[f'{date_col}_month'] = df_with_dates[date_col].dt.month
    df_with_dates[f'{date_col}_day'] = df_with_dates[date_col].dt.day
    df_with_dates[f'{date_col}_weekday'] = df_with_dates[date_col].dt.weekday
    df_with_dates[f'{date_col}_quarter'] = df_with_dates[date_col].dt.quarter
    df_with_dates[f'{date_col}_week'] = df_with_dates[date_col].dt.isocalendar().week
    
    return df_with_dates


def categorical_analysis(df: pd.DataFrame, cat_cols: Optional[List[str]] = None,
                        max_categories: int = 20) -> None:
    """
    Analyze categorical columns.
    
    Args:
        df: pandas DataFrame
        cat_cols: List of categorical columns
        max_categories: Maximum number of categories to display
    """
    if cat_cols is None:
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if plt is None:
        raise ImportError(
            "matplotlib is required for categorical_analysis. Install the visualization extras via"
            " `uv sync --extra viz` before using this helper."
        )

    for col in cat_cols:
        print(f"\n{'='*50}")
        print(f"ANALYSIS OF COLUMN: {col}")
        print(f"{'='*50}")
        
        value_counts = df[col].value_counts()
        print(f"Number of unique values: {df[col].nunique()}")
        print(f"Most frequent value: '{value_counts.index[0]}' ({value_counts.iloc[0]} occurrences)")
        
        if df[col].nunique() <= max_categories:
            print(f"\nValue counts:")
            print(value_counts)
            
            # Plot
            plt.figure(figsize=(12, 6))
            value_counts.plot(kind='bar')
            plt.title(f'Distribution of {col}')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        else:
            print(f"\nTop {max_categories} most frequent values:")
            print(value_counts.head(max_categories))
