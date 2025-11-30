import sys
import os
from pathlib import Path
import pandas as pd

# Add project root to path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from api.config import settings
from api.services import DataService

def debug_fleet_summary():
    print("="*50)
    print("DEBUGGING FLEET SUMMARY")
    print("="*50)
    
    print(f"Base Dir: {settings.BASE_DIR}")
    print(f"Processed Dir: {settings.DATA_PROCESSED_DIR}")
    
    csv_path = settings.DATA_PROCESSED_DIR / "biofouling_summary_by_ship.csv"
    print(f"CSV Path: {csv_path}")
    print(f"CSV Exists: {csv_path.exists()}")
    
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            print(f"CSV Loaded. Shape: {df.shape}")
            print("Columns:", df.columns.tolist())
            print("First row:", df.iloc[0].to_dict())
        except Exception as e:
            print(f"ERROR reading CSV: {e}")
    
    print("\nInitializing DataService...")
    service = DataService()
    
    print("Calling get_ship_summary()...")
    try:
        summary_df = service.get_ship_summary()
        print(f"Result Shape: {summary_df.shape}")
        
        if summary_df.empty:
            print("WARNING: Result is empty!")
        else:
            print("Result OK.")
            
            # Simulate endpoint logic
            print("\nSimulating Endpoint Logic...")
            row = summary_df.iloc[0]
            try:
                ship_data = {
                    'ship_name': row['shipName'],
                    'num_events': int(row.get('num_events', 0)),
                    'avg_excess_ratio': float(row.get('avg_excess_ratio', 0)),
                }
                print("Mapped first ship successfully:", ship_data)
            except Exception as e:
                print(f"ERROR mapping ship data: {e}")
                
    except Exception as e:
        print(f"ERROR calling get_ship_summary: {e}")

if __name__ == "__main__":
    debug_fleet_summary()
