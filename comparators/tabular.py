from typing import Dict, Any
from .base import FileComparator
import pandas as pd
from datacompy.core import Compare


class TabularComparator(FileComparator):
    """DataComPy-based tabular comparison"""
    
    def can_compare(self, file_path: str) -> bool:
        return file_path.lower().endswith(('.csv', '.tsv', '.xlsx', '.parquet'))
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        
        # Get read configuration
        comment_char = config.get('comment', None)
        skiprows = config.get('skiprows', None)

        def read(path):
            lower = path.lower()
            if lower.endswith('.parquet'):
                if comment_char is not None or 'skiprows' in config:
                    raise ValueError('comment/skiprows are unsupported for Parquet.')
                return pd.read_parquet(path)
            if lower.endswith('.xlsx'):
                if comment_char is not None:
                    raise ValueError('comment is unsupported for Excel.')
                return pd.read_excel(path, skiprows=skiprows)
            if not lower.endswith(('.csv', '.tsv')):
                raise ValueError(f'Unsupported table format: {path}')
            return pd.read_csv(path, sep='\t' if lower.endswith('.tsv') else ',',
                               comment=comment_char, skiprows=skiprows)

        df1, df2 = read(file1), read(file2)
        
        required = config.get('required_columns', [])
        missing1, missing2 = sorted(set(required) - set(df1.columns)), sorted(set(required) - set(df2.columns))
        if missing1 or missing2:
            return {'match': False, 'verdict': 'FAIL', 'method': 'datacompy',
                    'reason': f'Required columns missing: run1={missing1}, run2={missing2}',
                    'configuration': config}

        # Get configuration
        join_columns = config.get('join_columns', [df1.columns[0]])
        abs_tol = float(config.get('abs_tol', 1e-5))
        rel_tol = float(config.get('rel_tol', 0.01))
        
        # Ensure join_columns is a list
        if isinstance(join_columns, str):
            join_columns = [join_columns]
        
        # Create Compare object
        compare = Compare(
            df1, 
            df2,
            join_columns=join_columns,
            abs_tol=abs_tol,
            rel_tol=rel_tol,
            df1_name='df1',
            df2_name='df2'
        )
        
        # Get statistics - handle API differences
        def safe_get_count(obj, attr_name, method_name=None, default=0):
            """Safely get count from either attribute or method"""
            if hasattr(obj, attr_name):
                val = getattr(obj, attr_name)
                return len(val) if hasattr(val, '__len__') else val
            elif method_name and hasattr(obj, method_name):
                try:
                    return getattr(obj, method_name)()
                except:
                    return default
            return default
        
        # Extract row statistics
        rows_in_common = safe_get_count(compare, 'intersect_rows', 'count_matching_rows')
        rows_only_df1 = safe_get_count(compare, 'df1_unq_rows')
        rows_only_df2 = safe_get_count(compare, 'df2_unq_rows')
        
        # Calculate rows with differences
        # This is rows in common that don't match exactly
        rows_with_differences = 0
        if hasattr(compare, 'all_mismatch'):
            try:
                rows_with_differences = len(compare.all_mismatch())
            except:
                pass
        
        # Alternative: calculate from report if available
        if rows_with_differences == 0 and not compare.matches() and rows_in_common > 0:
            # If files don't match but rows are in common, some must differ
            rows_with_differences = rows_in_common  # Conservative estimate
        
        # Build result
        return {
            'match': compare.matches(),
            'method': 'datacompy',
            'configuration': {
                'join_columns': join_columns,
                'abs_tol': abs_tol,
                'rel_tol': rel_tol,
                'comment': comment_char,
                'skiprows': skiprows,
                'required_columns': required
            },
            'summary': {
                'rows_in_common': rows_in_common,
                'rows_only_in_df1': rows_only_df1,
                'rows_only_in_df2': rows_only_df2,
                'rows_with_differences': rows_with_differences,  # ADDED
            },
            'report': compare.report(),
            'verdict': 'PASS' if compare.matches() else 'FAIL',
            'reason': 'Outputs differ beyond tolerance' if not compare.matches() else None
        }
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        import datacompy
        return {
            '@type': 'SoftwareApplication',
            'name': 'DataComPy',
            'version': datacompy.__version__,
            'url': 'https://github.com/capitalone/datacompy',
            'applicationCategory': 'Tabular data comparison'
        }
