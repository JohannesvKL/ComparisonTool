from typing import Dict, Any
from .base import FileComparator


class HDF5Comparator(FileComparator):
    """HDF5 file comparison using h5diff concepts"""
    
    def can_compare(self, file_path: str) -> bool:
        return file_path.endswith(('.h5', '.hdf5'))
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        import h5py
        import numpy as np
        
        rtol = config.get('rtol', 1e-5)
        atol = config.get('atol', 1e-8)
        
        differences = []
        
        with h5py.File(file1, 'r') as f1, h5py.File(file2, 'r') as f2:
            # Compare datasets
            datasets1 = self._get_all_datasets(f1)
            datasets2 = self._get_all_datasets(f2)
            
            # Check for missing datasets
            only_in_f1 = set(datasets1.keys()) - set(datasets2.keys())
            only_in_f2 = set(datasets2.keys()) - set(datasets1.keys())
            
            if only_in_f1:
                differences.append(f"Datasets only in file1: {only_in_f1}")
            if only_in_f2:
                differences.append(f"Datasets only in file2: {only_in_f2}")
            
            # Compare common datasets
            for dataset_name in set(datasets1.keys()) & set(datasets2.keys()):
                data1 = datasets1[dataset_name][()]
                data2 = datasets2[dataset_name][()]
                
                if data1.shape != data2.shape:
                    differences.append(
                        f"{dataset_name}: shape mismatch {data1.shape} vs {data2.shape}"
                    )
                elif not np.allclose(data1, data2, rtol=rtol, atol=atol):
                    max_diff = np.max(np.abs(data1 - data2))
                    differences.append(
                        f"{dataset_name}: values differ (max diff: {max_diff})"
                    )
        
        match = len(differences) == 0
        
        return {
            'match': match,
            'method': 'hdf5_comparison',
            'configuration': {
                'rtol': rtol,
                'atol': atol
            },
            'summary': {
                'datasets_compared': len(set(datasets1.keys()) & set(datasets2.keys())),
                'differences_found': len(differences)
            },
            'differences': differences,
            'verdict': 'PASS' if match else 'FAIL',
            'reason': None if match else f'{len(differences)} differences found'
        }
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        return {
            '@type': 'SoftwareApplication',
            'name': 'h5py',
            'url': 'https://www.h5py.org/',
            'applicationCategory': 'HDF5 comparison'
        }
    
    def _get_all_datasets(self, hdf_file, prefix=''):
        """Recursively get all datasets in HDF5 file"""
        import h5py
        datasets = {}
        for key in hdf_file.keys():
            item = hdf_file[key]
            path = f"{prefix}/{key}" if prefix else key
            if isinstance(item, h5py.Dataset):
                datasets[path] = item
            elif isinstance(item, h5py.Group):
                datasets.update(self._get_all_datasets(item, path))
        return datasets