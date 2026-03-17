from typing import Dict, Any
from .base import FileComparator


class ImageComparator(FileComparator):
    """Image comparison using SSIM"""
    
    def can_compare(self, file_path: str) -> bool:
        return file_path.endswith(('.png', '.jpg', '.jpeg', '.tiff'))
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        from skimage import io, metrics
        
        # Load images
        img1 = io.imread(file1)
        img2 = io.imread(file2)
        
        # Check dimensions match
        if img1.shape != img2.shape:
            return {
                'match': False,
                'method': 'ssim',
                'verdict': 'FAIL',
                'reason': f'Image dimensions differ: {img1.shape} vs {img2.shape}'
            }
        
        # Compute SSIM
        threshold = config.get('ssim_threshold', 0.95)

        # Determine appropriate win_size for small images.
        # SSIM requires an odd win_size <= the smallest image dimension.
        # Fall back to pixel comparison if the image is too small to be meaningful.
        min_dim = min(img1.shape[:2])
        if min_dim < 3:
            # Image too small for SSIM — use exact pixel comparison instead
            import numpy as np
            match = np.array_equal(img1, img2)
            return {
                'match': match,
                'method': 'pixel',
                'configuration': {'threshold': threshold},
                'metrics': {'pixel_equal': match},
                'verdict': 'PASS' if match else 'FAIL',
                'reason': (
                    f'Image too small for SSIM ({img1.shape}), used pixel comparison'
                    if match else
                    f'Images differ (pixel comparison, size {img1.shape})'
                )
            }

        # Pick largest odd win_size that fits
        win_size = config.get('win_size', None)
        if win_size is None:
            win_size = min(7, min_dim)
            if win_size % 2 == 0:
                win_size -= 1

        # Handle color vs grayscale
        if len(img1.shape) == 3:
            ssim_value = metrics.structural_similarity(
                img1, img2,
                channel_axis=2,
                win_size=win_size
            )
        else:
            ssim_value = metrics.structural_similarity(
                img1, img2,
                win_size=win_size
            )
        
        match = ssim_value >= threshold
        
        return {
            'match': match,
            'method': 'ssim',
            'configuration': {
                'threshold': threshold,
                'win_size': win_size
            },
            'metrics': {
                'ssim': float(ssim_value),
                'threshold': threshold
            },
            'verdict': 'PASS' if match else 'FAIL',
            'reason': None if match else f'SSIM {ssim_value:.4f} below threshold {threshold}'
        }
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        return {
            '@type': 'SoftwareApplication',
            'name': 'scikit-image SSIM',
            'url': 'https://scikit-image.org/',
            'applicationCategory': 'Image comparison'
        }