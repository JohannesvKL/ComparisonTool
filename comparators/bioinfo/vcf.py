"""
VCF file comparator using pysam/cyvcf2
"""

from typing import Dict, Any, Set, Tuple, List
import sys
sys.path.append('..')
from comparators.base import FileComparator


class VcfComparator(FileComparator):
    """
    Compare VCF (Variant Call Format) files
    
    Supports multiple comparison modes:
    - positions: Compare variant positions only (CHROM, POS, REF, ALT)
    - genotypes: Compare genotypes for all samples
    - full: Compare all fields including INFO and FORMAT
    - quality: Compare with quality score tolerance
    
    Handles both single-sample and multi-sample VCFs.
    """
    
    def can_compare(self, file_path: str) -> bool:
        """Check if file is VCF format"""
        return file_path.endswith(('.vcf', '.vcf.gz', '.bcf'))
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        """
        Compare two VCF files
        
        Config options:
            mode: 'positions' | 'genotypes' | 'full' (default: 'genotypes')
            quality_tolerance: float (default: 0.01) - relative tolerance for quality scores
            ignore_filters: bool (default: False) - ignore FILTER column
            ignore_info: bool (default: False) - ignore INFO fields
            ignore_format: bool (default: False) - ignore FORMAT fields
            sample_subset: list - only compare these samples (default: all)
            check_order: bool (default: False) - require same variant order
        """
        # Try to import pysam first (preferred), fall back to cyvcf2
        try:
            import pysam
            return self._compare_with_pysam(file1, file2, config)
        except ImportError:
            try:
                from cyvcf2 import VCF
                return self._compare_with_cyvcf2(file1, file2, config)
            except ImportError:
                return {
                    'match': False,
                    'method': 'vcf_comparison',
                    'verdict': 'ERROR',
                    'reason': 'Neither pysam nor cyvcf2 installed. Install with: pip install pysam (or cyvcf2)'
                }
    
    def _compare_with_pysam(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        """Compare VCF files using pysam"""
        import pysam
        
        # Get configuration
        mode = config.get('mode', 'genotypes')
        quality_tol = config.get('quality_tolerance', 0.01)
        ignore_filters = config.get('ignore_filters', False)
        ignore_info = config.get('ignore_info', False)
        ignore_format = config.get('ignore_format', False)
        sample_subset = config.get('sample_subset', None)
        check_order = config.get('check_order', False)
        
        # Open VCF files
        try:
            vcf1 = pysam.VariantFile(file1)
            vcf2 = pysam.VariantFile(file2)
        except Exception as e:
            return {
                'match': False,
                'method': 'vcf_comparison',
                'verdict': 'ERROR',
                'reason': f'Failed to open VCF files: {e}'
            }
        
        # Compare headers
        header_match, header_info = self._compare_headers_pysam(
            vcf1.header, vcf2.header, ignore_info, ignore_format
        )
        
        # Compare samples
        samples1 = list(vcf1.header.samples)
        samples2 = list(vcf2.header.samples)
        
        if sample_subset:
            samples_to_compare = sample_subset
            samples_match = all(s in samples1 and s in samples2 for s in samples_to_compare)
        else:
            samples_to_compare = samples1
            samples_match = set(samples1) == set(samples2)
        
        # Compare variants based on mode
        if mode == 'positions':
            variants_match, variant_info = self._compare_positions_pysam(
                vcf1, vcf2, check_order
            )
        elif mode == 'genotypes':
            variants_match, variant_info = self._compare_genotypes_pysam(
                vcf1, vcf2, samples_to_compare, check_order, quality_tol
            )
        elif mode == 'full':
            variants_match, variant_info = self._compare_full_pysam(
                vcf1, vcf2, samples_to_compare, check_order, quality_tol,
                ignore_filters, ignore_info, ignore_format
            )
        else:
            vcf1.close()
            vcf2.close()
            return {
                'match': False,
                'method': 'vcf_comparison',
                'verdict': 'ERROR',
                'reason': f"Unknown mode: {mode}. Use 'positions', 'genotypes', or 'full'"
            }
        
        vcf1.close()
        vcf2.close()
        
        match = header_match and samples_match and variants_match
        
        return {
            'match': match,
            'method': 'vcf_comparison',
            'mode': mode,
            'configuration': {
                'quality_tolerance': quality_tol,
                'ignore_filters': ignore_filters,
                'ignore_info': ignore_info,
                'ignore_format': ignore_format,
                'check_order': check_order
            },
            'summary': {
                'header_matches': header_match,
                'samples_match': samples_match,
                'variants_match': variants_match,
                'samples_file1': samples1,
                'samples_file2': samples2,
                'samples_compared': samples_to_compare,
                **header_info,
                **variant_info
            },
            'verdict': 'PASS' if match else 'FAIL',
            'reason': self._build_failure_reason(
                header_match, samples_match, variants_match, variant_info
            )
        }
    
    def _compare_headers_pysam(self, header1, header2, 
                               ignore_info: bool, ignore_format: bool) -> Tuple[bool, Dict]:
        """Compare VCF headers"""
        # Get contigs
        contigs1 = set(header1.contigs.keys())
        contigs2 = set(header2.contigs.keys())
        
        contigs_match = contigs1 == contigs2
        
        # Compare INFO fields if not ignored
        if not ignore_info:
            info1 = set(header1.info.keys())
            info2 = set(header2.info.keys())
            info_match = info1 == info2
        else:
            info_match = True
            info1 = info2 = set()
        
        # Compare FORMAT fields if not ignored
        if not ignore_format:
            format1 = set(header1.formats.keys())
            format2 = set(header2.formats.keys())
            format_match = format1 == format2
        else:
            format_match = True
            format1 = format2 = set()
        
        match = contigs_match and info_match and format_match
        
        info = {
            'contigs_match': contigs_match,
            'contigs_only_in_file1': list(contigs1 - contigs2),
            'contigs_only_in_file2': list(contigs2 - contigs1),
            'info_fields_match': info_match,
            'format_fields_match': format_match
        }
        
        return match, info
    
    def _compare_positions_pysam(self, vcf1, vcf2, 
                                 check_order: bool) -> Tuple[bool, Dict]:
        """Compare variant positions only (CHROM, POS, REF, ALT)"""
        variants1 = []
        variants2 = []
        
        # Extract variants
        for record in vcf1:
            for alt in record.alts:
                variant = (record.chrom, record.pos, record.ref, alt)
                variants1.append(variant)
        
        for record in vcf2:
            for alt in record.alts:
                variant = (record.chrom, record.pos, record.ref, alt)
                variants2.append(variant)
        
        if check_order:
            # Order matters
            match = variants1 == variants2
            only_in_1 = 0
            only_in_2 = 0
        else:
            # Order doesn't matter - use sets
            set1 = set(variants1)
            set2 = set(variants2)
            
            only_in_1 = len(set1 - set2)
            only_in_2 = len(set2 - set1)
            
            match = only_in_1 == 0 and only_in_2 == 0
        
        info = {
            'total_variants_file1': len(variants1),
            'total_variants_file2': len(variants2),
            'variants_only_in_file1': only_in_1,
            'variants_only_in_file2': only_in_2
        }
        
        return match, info
    
    def _compare_genotypes_pysam(self, vcf1, vcf2, samples: List[str],
                                 check_order: bool, quality_tol: float) -> Tuple[bool, Dict]:
        """Compare genotypes for specified samples"""
        variants1 = {}
        variants2 = {}
        
        # Extract variants with genotypes
        for record in vcf1:
            for alt in record.alts:
                pos_key = (record.chrom, record.pos, record.ref, alt)
                
                # Get genotypes for samples
                genotypes = {}
                for sample in samples:
                    if sample in record.samples:
                        gt = record.samples[sample]['GT']
                        genotypes[sample] = gt
                
                variants1[pos_key] = {
                    'genotypes': genotypes,
                    'quality': record.qual
                }
        
        for record in vcf2:
            for alt in record.alts:
                pos_key = (record.chrom, record.pos, record.ref, alt)
                
                genotypes = {}
                for sample in samples:
                    if sample in record.samples:
                        gt = record.samples[sample]['GT']
                        genotypes[sample] = gt
                
                variants2[pos_key] = {
                    'genotypes': genotypes,
                    'quality': record.qual
                }
        
        # Compare
        positions1 = set(variants1.keys())
        positions2 = set(variants2.keys())
        
        only_in_1 = positions1 - positions2
        only_in_2 = positions2 - positions1
        common = positions1 & positions2
        
        # For common variants, check genotypes
        genotype_differences = []
        quality_differences = []
        
        for pos in common:
            # Compare genotypes
            gt1 = variants1[pos]['genotypes']
            gt2 = variants2[pos]['genotypes']
            
            if gt1 != gt2:
                genotype_differences.append(pos)
            
            # Compare quality with tolerance
            qual1 = variants1[pos]['quality']
            qual2 = variants2[pos]['quality']
            
            if qual1 is not None and qual2 is not None:
                if not self._quality_close(qual1, qual2, quality_tol):
                    quality_differences.append(pos)
        
        match = (
            len(only_in_1) == 0 and 
            len(only_in_2) == 0 and 
            len(genotype_differences) == 0
        )
        
        info = {
            'variants_in_common': len(common),
            'variants_only_in_file1': len(only_in_1),
            'variants_only_in_file2': len(only_in_2),
            'genotype_differences': len(genotype_differences),
            'quality_differences': len(quality_differences),
            'quality_differences_positions': list(quality_differences)[:10]
        }
        
        return match, info
    
    def _compare_full_pysam(self, vcf1, vcf2, samples: List[str],
                           check_order: bool, quality_tol: float,
                           ignore_filters: bool, ignore_info: bool,
                           ignore_format: bool) -> Tuple[bool, Dict]:
        """Full comparison including INFO and FORMAT fields"""
        variants1 = {}
        variants2 = {}
        
        # Extract all variant information
        for record in vcf1:
            for alt in record.alts:
                pos_key = (record.chrom, record.pos, record.ref, alt)
                
                variant_data = {
                    'quality': record.qual,
                    'filter': None if ignore_filters else record.filter.keys(),
                    'info': {} if ignore_info else dict(record.info),
                    'genotypes': {},
                    'format': {}
                }
                
                # Get sample data
                for sample in samples:
                    if sample in record.samples:
                        variant_data['genotypes'][sample] = record.samples[sample]['GT']
                        
                        if not ignore_format:
                            # Get all FORMAT fields
                            for fmt_key in record.format.keys():
                                if fmt_key != 'GT':
                                    try:
                                        value = record.samples[sample][fmt_key]
                                        if sample not in variant_data['format']:
                                            variant_data['format'][sample] = {}
                                        variant_data['format'][sample][fmt_key] = value
                                    except:
                                        pass
                
                variants1[pos_key] = variant_data
        
        # Same for file2
        for record in vcf2:
            for alt in record.alts:
                pos_key = (record.chrom, record.pos, record.ref, alt)
                
                variant_data = {
                    'quality': record.qual,
                    'filter': None if ignore_filters else record.filter.keys(),
                    'info': {} if ignore_info else dict(record.info),
                    'genotypes': {},
                    'format': {}
                }
                
                for sample in samples:
                    if sample in record.samples:
                        variant_data['genotypes'][sample] = record.samples[sample]['GT']
                        
                        if not ignore_format:
                            for fmt_key in record.format.keys():
                                if fmt_key != 'GT':
                                    try:
                                        value = record.samples[sample][fmt_key]
                                        if sample not in variant_data['format']:
                                            variant_data['format'][sample] = {}
                                        variant_data['format'][sample][fmt_key] = value
                                    except:
                                        pass
                
                variants2[pos_key] = variant_data
        
        # Compare
        positions1 = set(variants1.keys())
        positions2 = set(variants2.keys())
        
        only_in_1 = positions1 - positions2
        only_in_2 = positions2 - positions1
        common = positions1 & positions2
        
        differences = {
            'genotypes': [],
            'quality': [],
            'filters': [],
            'info': [],
            'format': []
        }
        
        for pos in common:
            v1 = variants1[pos]
            v2 = variants2[pos]
            
            # Compare genotypes
            if v1['genotypes'] != v2['genotypes']:
                differences['genotypes'].append(pos)
            
            # Compare quality
            if v1['quality'] is not None and v2['quality'] is not None:
                if not self._quality_close(v1['quality'], v2['quality'], quality_tol):
                    differences['quality'].append(pos)
            
            # Compare filters
            if not ignore_filters and v1['filter'] != v2['filter']:
                differences['filters'].append(pos)
            
            # Compare INFO
            if not ignore_info and v1['info'] != v2['info']:
                differences['info'].append(pos)
            
            # Compare FORMAT
            if not ignore_format and v1['format'] != v2['format']:
                differences['format'].append(pos)
        
        match = (
            len(only_in_1) == 0 and
            len(only_in_2) == 0 and
            all(len(diffs) == 0 for diffs in differences.values())
        )
        
        info = {
            'variants_in_common': len(common),
            'variants_only_in_file1': len(only_in_1),
            'variants_only_in_file2': len(only_in_2),
            'genotype_differences': len(differences['genotypes']),
            'quality_differences': len(differences['quality']),
            'filter_differences': len(differences['filters']),
            'info_differences': len(differences['info']),
            'format_differences': len(differences['format'])
        }
        
        return match, info
    
    def _quality_close(self, qual1: float, qual2: float, tolerance: float) -> bool:
        """Check if quality scores are close within tolerance"""
        if qual1 == qual2:
            return True
        
        # Relative tolerance
        max_qual = max(abs(qual1), abs(qual2))
        if max_qual == 0:
            return True
        
        rel_diff = abs(qual1 - qual2) / max_qual
        return rel_diff <= tolerance
    
    
    def _build_failure_reason(self, header_match: bool, samples_match: bool,
                             variants_match: bool, variant_info: Dict) -> str:
        """Build human-readable failure reason"""
        if header_match and samples_match and variants_match:
            return None
        
        reasons = []
        
        if not header_match:
            reasons.append("headers differ")
        
        if not samples_match:
            reasons.append("sample lists differ")
        
        if not variants_match:
            parts = []
            if variant_info.get('variants_only_in_file1', 0) > 0:
                parts.append(f"{variant_info['variants_only_in_file1']} variants only in file1")
            if variant_info.get('variants_only_in_file2', 0) > 0:
                parts.append(f"{variant_info['variants_only_in_file2']} variants only in file2")
            if variant_info.get('genotype_differences', 0) > 0:
                parts.append(f"{variant_info['genotype_differences']} genotype differences")
            
            if parts:
                reasons.append(', '.join(parts))
            else:
                reasons.append("variants differ")
        
        return '; '.join(reasons)
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        """Return metadata about VCF comparison tools"""
        try:
            import pysam
            version = pysam.__version__
            tool = 'pysam'
        except ImportError:
            version = "not installed"
            tool = "none"
        
        return {
            '@type': 'SoftwareApplication',
            'name': f'VCF Comparator ({tool})',
            'version': version,
            'url': 'https://pysam.readthedocs.io/' ,
            'applicationCategory': 'VCF file comparison'
        }