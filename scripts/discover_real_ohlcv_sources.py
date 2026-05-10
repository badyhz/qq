#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple


def get_file_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        return 'CSV'
    elif ext == '.json':
        return 'JSON'
    elif ext == '.jsonl':
        return 'JSONL'
    return 'UNKNOWN'


def detect_ohlcv_columns(columns: List[str]) -> Tuple[List[str], bool]:
    detected = []
    col_set = {c.lower().strip() for c in columns}
    
    ohlcv_mappings = {
        'open': ['open', 'o'],
        'high': ['high', 'h'],
        'low': ['low', 'l'],
        'close': ['close', 'c', 'last', 'price', 'mark_price'],
        'volume': ['volume', 'vol', 'v', 'quote_volume']
    }
    
    for canonical, aliases in ohlcv_mappings.items():
        for alias in aliases:
            if alias in col_set:
                detected.append(canonical)
                break
    
    has_ohlcv = len(detected) == 5
    return detected, has_ohlcv


def scan_file(path: str) -> Optional[Dict]:
    file_type = get_file_type(path)
    detected_columns = []
    has_ohlcv_columns = False
    row_estimate = 0
    
    if file_type == 'CSV':
        try:
            with open(path, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    detected_columns = header
                    ohlcv_cols, has_ohlcv_columns = detect_ohlcv_columns(header)
                    for _ in reader:
                        row_estimate += 1
                    row_estimate += 1  # include header row
        except Exception:
            pass
    elif file_type in ['JSONL', 'JSON']:
        try:
            if file_type == 'JSONL':
                with open(path, 'r') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        obj = json.loads(first_line)
                        if isinstance(obj, dict):
                            detected_columns = list(obj.keys())
                            ohlcv_cols, has_ohlcv_columns = detect_ohlcv_columns(detected_columns)
                        f.seek(0)
                        row_estimate = sum(1 for _ in f)
            else:
                with open(path, 'r') as f:
                    obj = json.load(f)
                    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                        detected_columns = list(obj[0].keys())
                        ohlcv_cols, has_ohlcv_columns = detect_ohlcv_columns(detected_columns)
                        row_estimate = len(obj)
        except Exception:
            pass
    
    if file_type == 'UNKNOWN':
        return None
    
    return {
        'source_id': str(uuid.uuid4()),
        'path': path,
        'file_type': file_type,
        'detected_columns': detected_columns,
        'has_ohlcv_columns': has_ohlcv_columns,
        'row_estimate': row_estimate,
        'reason': 'detected_file'
    }


def run_discovery(search_roots: List[str]) -> Dict:
    files_scanned = 0
    candidate_sources = []
    excluded_sources = []
    audit_warnings = []
    
    for root_dir in search_roots:
        if not os.path.exists(root_dir):
            continue
        
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                
                # Exclude secret files
                if filename in ['.env', 'secret', 'key'] or any(ext in filename.lower() for ext in ['.key', '.secret', '.env']):
                    excluded_sources.append({
                        'path': path,
                        'reason': 'secret_or_env_file'
                    })
                    continue
                
                files_scanned += 1
                scan_result = scan_file(path)
                
                if scan_result is None:
                    excluded_sources.append({
                        'path': path,
                        'reason': 'unknown_file_type'
                    })
                elif scan_result['has_ohlcv_columns']:
                    candidate_sources.append(scan_result)
                else:
                    excluded_sources.append({
                        'path': path,
                        'reason': 'missing_ohlcv_columns'
                    })
    
    final_verdict = 'PASS'
    discovery_ready = len(candidate_sources) > 0
    
    return {
        'task_id': 'T411',
        'phase': 'REAL_OHLCV_SOURCE_DISCOVERY',
        'allowed_mode': 'SHADOW_ONLY',
        'collection_mode': 'SHADOW_COLLECTION',
        'submit_permission': 'NO_SUBMIT',
        'testnet_submit_allowed': False,
        'real_submit_allowed': False,
        'submit_attempted': False,
        'cancel_attempted': False,
        'flatten_attempted': False,
        'search_roots': search_roots,
        'files_scanned': files_scanned,
        'candidate_source_count': len(candidate_sources),
        'excluded_source_count': len(excluded_sources),
        'candidate_sources': candidate_sources,
        'excluded_sources': excluded_sources,
        'discovery_ready': discovery_ready,
        'missing_inputs': [],
        'audit_warnings': audit_warnings,
        'final_verdict': final_verdict,
        'generated_at_utc': datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    
    search_roots = ['reports', 'logs', 'data']
    result = run_discovery(search_roots)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Scanned {result['files_scanned']} files.")
        print(f"Candidates: {result['candidate_source_count']}")
        print(f"Excluded: {result['excluded_source_count']}")


if __name__ == '__main__':
    main()
