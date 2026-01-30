"""Remove category from expected_filters in golden dataset."""

from src.evaluation.datasets.golden_dataset import GoldenDataset

ds = GoldenDataset.load('data/evaluation/golden_dataset.json')

for q in ds.queries:
    if 'category' in q.expected_filters:
        q.expected_filters = {k: v for k, v in q.expected_filters.items() if k != 'category'}

ds.save('data/evaluation/golden_dataset.json')
print('Removed category from all expected_filters')
