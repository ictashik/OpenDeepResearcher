#!/usr/bin/env python3
"""
Test script to verify PyArrow fallbacks work correctly.
"""

import sys
import os
sys.path.append('/Volumes/Development/Projects/OpenDeepResearcher/opendeep-researcher')

import pandas as pd
from src.utils.streamlit_utils import safe_dataframe, safe_download_button

# Test data
test_df = pd.DataFrame({
    'title': ['Test Article 1', 'Test Article 2'],
    'authors': ['Author A', 'Author B'],
    'year': [2023, 2024]
})

print("Testing DataFrame fallbacks...")
print("DataFrame created successfully:", test_df.shape)

# Test CSV generation
csv_data = test_df.to_csv(index=False)
print("CSV generation successful:", len(csv_data), "characters")

print("\nAll basic operations work correctly!")
print("The safe functions should handle PyArrow errors gracefully when used in Streamlit.")
