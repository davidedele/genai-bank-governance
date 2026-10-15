"""Read the versioned synthetic benchmark. Labels are not expert consensus."""
import json
from pathlib import Path
DATASET_PATH = Path(__file__).with_name('benchmark.json')
DATASET = json.loads(DATASET_PATH.read_text(encoding='utf-8'))
CASES = DATASET['cases']
