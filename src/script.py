import os
import sys
import logging
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Config:
    # Project structure paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
    SRC_DIR = os.path.join(BASE_DIR, 'src')
    DATA_RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
    DATA_PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    CONFIG_DIR = os.path.join(BASE_DIR, 'config')
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

    FILE_EVENTS = 'ResultadoQueryEventos.csv'
    FILE_CONSUMPTION = 'ResultadoQueryConsumo.csv'
    FILE_DRYDOCK = 'Dados navios Hackathon.xlsx'
    SHEET_DRYDOCK = 'Lista de docagens'
    FILE_PAINT = 'Dados navios Hackathon.xlsx - Especificacao revestimento.csv'
    SHEET_PAINT = 'Especificacao revestimento'

    COL_SHIP_NAME = 'shipName'
    COL_START_DATE = 'startGMTDate'
    COL_DOCAGEM_DATE = 'Docagem'
    COL_DOCAGEM_SHIP = 'Navio'
    COL_SESSION_ID = 'sessionId'
    COL_SESSION_ID_CONSUMPTION = 'SESSION_ID'
    COL_CONSUMPTION = 'CONSUMED_QUANTITY'
    COL_SPEED = 'speed'
    COL_DURATION = 'duration'
    COL_DISPLACEMENT = 'displacement'
    COL_DRAFT = 'midDraft'
    COL_PAINT_TYPE = 'Tipo'

    IDLE_SPEED_THRESHOLD = 5.0
    ROLLING_WINDOW_DAYS = '30D'
    PAINT_PENALTY_THRESHOLD = 0.3
    PAINT_PENALTY_FACTOR = 0.8
    SPC_PAINT_KEYWORD = 'SPC'
    ADMIRALTY_SCALE_FACTOR = 10000.0
    MIN_CONSUMPTION_THRESHOLD = 0.1

    TRAIN_TEST_SPLIT_RATIO = 0.80
    VALIDATION_SPLIT_RATIO = 0.90

    MODEL_PARAMS = {
        'objective': 'reg:squarederror',
        'n_estimators': 300,
        'learning_rate': 0.03,
        'max_depth': 5,
        'min_child_weight': 10,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 1.0,
        'reg_lambda': 2.0,
        'n_jobs': -1,
        'random_state': 42,
        'early_stopping_rounds': 30
    }

    MODEL_OUTPUT = 'modelo_final_v13.pkl'
    ENCODER_OUTPUT = 'encoder_final_v13.pkl'
    # Biofouling/report parameters
    BIO_REFERENCE = None  # Set to None for dynamic (percentile 75), or fixed value like 0.20
    BIO_REFERENCE_PERCENTILE = 0.75  # Used when BIO_REFERENCE is None
    USE_SIGMOID_SCALE = True  # Use sigmoid for smoother bio_index transition
    SIGMOID_K = 10  # Sigmoid steepness (higher = sharper transition)
    SIGMOID_MIDPOINT = 0.10  # ER value at sigmoid midpoint (bio_index = 0.5)
    CALIBRATE_PER_SHIP = True  # Calibrate efficiency factor per ship (more accurate)
    FUEL_PRICE_USD_PER_TON = 500  # USD per ton of fuel (set to None to disable cost estimates)
    CO2_TON_PER_FUEL_TON = 3.114  # default tCO2 per t fuel (approx. for HFO/MSFO)
    REPORT_OUTPUT = 'biofouling_report.csv'
    SUMMARY_OUTPUT = 'biofouling_summary_by_ship.csv'


# =============================================================================
# ALGORITHM PARAMETER PRINTER FUNCTION
# =============================================================================
def print_algorithm_parameters():
    """
    Print all algorithm parameters used for data processing and model training.
    
    This function logs all configuration parameters from the Config class,
    organized by category for better understanding and debugging.
    Useful for filtering and understanding external API data processing.
    
    Returns:
        dict: A dictionary containing all algorithm parameters organized by category.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Build parameter dictionary organized by category
        parameters = {
            # -----------------------------------------------------------------
            # DATA SOURCE PARAMETERS
            # -----------------------------------------------------------------
            "data_sources": {
                "base_directory": Config.BASE_DIR,
                "data_raw_directory": Config.DATA_RAW_DIR,
                "data_processed_directory": Config.DATA_PROCESSED_DIR,
                "models_directory": Config.MODELS_DIR,
                "events_file": Config.FILE_EVENTS,
                "consumption_file": Config.FILE_CONSUMPTION,
                "drydock_file": Config.FILE_DRYDOCK,
                "drydock_sheet": Config.SHEET_DRYDOCK,
                "paint_file": Config.FILE_PAINT,
                "paint_sheet": Config.SHEET_PAINT,
            },
            
            # -----------------------------------------------------------------
            # COLUMN MAPPING PARAMETERS
            # -----------------------------------------------------------------
            "column_mapping": {
                "ship_name_column": Config.COL_SHIP_NAME,
                "start_date_column": Config.COL_START_DATE,
                "docagem_date_column": Config.COL_DOCAGEM_DATE,
                "docagem_ship_column": Config.COL_DOCAGEM_SHIP,
                "session_id_column": Config.COL_SESSION_ID,
                "session_id_consumption_column": Config.COL_SESSION_ID_CONSUMPTION,
                "consumption_column": Config.COL_CONSUMPTION,
                "speed_column": Config.COL_SPEED,
                "duration_column": Config.COL_DURATION,
                "displacement_column": Config.COL_DISPLACEMENT,
                "draft_column": Config.COL_DRAFT,
                "paint_type_column": Config.COL_PAINT_TYPE,
            },
            
            # -----------------------------------------------------------------
            # FEATURE ENGINEERING PARAMETERS
            # -----------------------------------------------------------------
            "feature_engineering": {
                "idle_speed_threshold_knots": Config.IDLE_SPEED_THRESHOLD,
                "rolling_window_days": Config.ROLLING_WINDOW_DAYS,
                "paint_penalty_threshold": Config.PAINT_PENALTY_THRESHOLD,
                "paint_penalty_factor": Config.PAINT_PENALTY_FACTOR,
                "spc_paint_keyword": Config.SPC_PAINT_KEYWORD,
                "admiralty_scale_factor": Config.ADMIRALTY_SCALE_FACTOR,
                "min_consumption_threshold": Config.MIN_CONSUMPTION_THRESHOLD,
            },
            
            # -----------------------------------------------------------------
            # MODEL TRAINING PARAMETERS
            # -----------------------------------------------------------------
            "model_training": {
                "train_test_split_ratio": Config.TRAIN_TEST_SPLIT_RATIO,
                "validation_split_ratio": Config.VALIDATION_SPLIT_RATIO,
                "model_output_file": Config.MODEL_OUTPUT,
                "encoder_output_file": Config.ENCODER_OUTPUT,
            },
            
            # -----------------------------------------------------------------
            # XGBOOST HYPERPARAMETERS
            # -----------------------------------------------------------------
            "xgboost_params": Config.MODEL_PARAMS,
            
            # -----------------------------------------------------------------
            # BIOFOULING INDEX PARAMETERS
            # -----------------------------------------------------------------
            "biofouling_config": {
                "bio_reference": Config.BIO_REFERENCE,
                "bio_reference_percentile": Config.BIO_REFERENCE_PERCENTILE,
                "use_sigmoid_scale": Config.USE_SIGMOID_SCALE,
                "sigmoid_k": Config.SIGMOID_K,
                "sigmoid_midpoint": Config.SIGMOID_MIDPOINT,
                "calibrate_per_ship": Config.CALIBRATE_PER_SHIP,
            },
            
            # -----------------------------------------------------------------
            # COST AND EMISSIONS PARAMETERS
            # -----------------------------------------------------------------
            "cost_emissions": {
                "fuel_price_usd_per_ton": Config.FUEL_PRICE_USD_PER_TON,
                "co2_ton_per_fuel_ton": Config.CO2_TON_PER_FUEL_TON,
            },
            
            # -----------------------------------------------------------------
            # OUTPUT FILES
            # -----------------------------------------------------------------
            "output_files": {
                "report_output": Config.REPORT_OUTPUT,
                "summary_output": Config.SUMMARY_OUTPUT,
            },
        }
        
        # Print header
        logger.info("=" * 80)
        logger.info("ALGORITHM PARAMETERS - BIOFOULING PREDICTION MODEL")
        logger.info("=" * 80)
        
        # Print each category
        for category, params in parameters.items():
            logger.info("")
            logger.info(f">>> {category.upper().replace('_', ' ')}")
            logger.info("-" * 40)
            
            if isinstance(params, dict):
                for key, value in params.items():
                    # Format the key for better readability
                    formatted_key = key.replace('_', ' ').title()
                    logger.info(f"  {formatted_key}: {value}")
            else:
                logger.info(f"  {params}")
        
        # Print footer with summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("PARAMETER SUMMARY")
        logger.info("=" * 80)
        logger.info(f"  Total Categories: {len(parameters)}")
        total_params = sum(
            len(v) if isinstance(v, dict) else 1 
            for v in parameters.values()
        )
        logger.info(f"  Total Parameters: {total_params}")
        logger.info(f"  XGBoost Estimators: {Config.MODEL_PARAMS.get('n_estimators', 'N/A')}")
        logger.info(f"  Learning Rate: {Config.MODEL_PARAMS.get('learning_rate', 'N/A')}")
        logger.info(f"  Max Depth: {Config.MODEL_PARAMS.get('max_depth', 'N/A')}")
        logger.info("=" * 80)
        logger.info("Parameters printed successfully!")
        logger.info("")
        
        return parameters
        
    except Exception as e:
        logger.error(f"Error printing algorithm parameters: {e}")
        raise

def load_data():
    try:
        path_events = os.path.join(Config.DATA_RAW_DIR, Config.FILE_EVENTS)
        path_consumption = os.path.join(Config.DATA_RAW_DIR, Config.FILE_CONSUMPTION)
        path_drydock = os.path.join(Config.DATA_RAW_DIR, Config.FILE_DRYDOCK)

        df_events = pd.read_csv(path_events)
        df_consumption = pd.read_csv(path_consumption)
        # Aggregate consumption by SESSION_ID (sum) to avoid duplicates from multiple fuel types
        df_consumption[Config.COL_CONSUMPTION] = pd.to_numeric(df_consumption[Config.COL_CONSUMPTION], errors='coerce')
        df_consumption = df_consumption.groupby(Config.COL_SESSION_ID_CONSUMPTION, as_index=False)[Config.COL_CONSUMPTION].sum()
        df_drydock = pd.read_excel(path_drydock, sheet_name=Config.SHEET_DRYDOCK)

        path_paint_csv = os.path.join(Config.DATA_RAW_DIR, Config.FILE_PAINT)
        if os.path.exists(path_paint_csv):
            df_paint = pd.read_csv(path_paint_csv)
        else:
            df_paint = pd.read_excel(path_drydock, sheet_name=Config.SHEET_PAINT)

        df_events[Config.COL_START_DATE] = pd.to_datetime(df_events[Config.COL_START_DATE])
        df_drydock[Config.COL_DOCAGEM_DATE] = pd.to_datetime(df_drydock[Config.COL_DOCAGEM_DATE])

        df_events[Config.COL_SHIP_NAME] = df_events[Config.COL_SHIP_NAME].astype(str).str.upper().str.strip()
        df_drydock[Config.COL_DOCAGEM_SHIP] = df_drydock[Config.COL_DOCAGEM_SHIP].astype(str).str.upper().str.strip()

        if 'Nome do navio' in df_paint.columns:
            df_paint = df_paint.rename(columns={'Nome do navio': Config.COL_SHIP_NAME})
        elif 'Navio' in df_paint.columns:
            df_paint = df_paint.rename(columns={'Navio': Config.COL_SHIP_NAME})

        if Config.COL_SHIP_NAME in df_paint.columns:
            df_paint[Config.COL_SHIP_NAME] = df_paint[Config.COL_SHIP_NAME].astype(str).str.upper().str.strip()

        return df_events, df_consumption, df_drydock, df_paint
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        sys.exit(1)

def feature_engineering_events(df):
    df = df.sort_values([Config.COL_SHIP_NAME, Config.COL_START_DATE])

    df['idle_hours'] = np.where(df[Config.COL_SPEED] < Config.IDLE_SPEED_THRESHOLD, df[Config.COL_DURATION], 0)

    indexer = df.set_index(Config.COL_START_DATE).groupby(Config.COL_SHIP_NAME)

    rolling_idle_sum = indexer['idle_hours'].rolling(window=Config.ROLLING_WINDOW_DAYS, min_periods=1).sum().shift(1)
    rolling_total_sum = indexer[Config.COL_DURATION].rolling(window=Config.ROLLING_WINDOW_DAYS, min_periods=1).sum().shift(1)

    rolling_stats = pd.DataFrame({
        'sum_idle': rolling_idle_sum,
        'sum_total': rolling_total_sum
    }).reset_index()

    rolling_stats['pct_idle_recent'] = rolling_stats['sum_idle'] / (rolling_stats['sum_total'] + 1e-6)

    df = pd.merge(
        df,
        rolling_stats[[Config.COL_SHIP_NAME, Config.COL_START_DATE, 'pct_idle_recent']],
        on=[Config.COL_SHIP_NAME, Config.COL_START_DATE],
        how='left'
    )

    df['historical_avg_speed'] = (
        df.groupby(Config.COL_SHIP_NAME)[Config.COL_SPEED]
        .transform(lambda x: x.rolling(window=10, min_periods=1).mean().shift(1))
    )

    return df

def feature_engineering_combined(df):
    df['is_SPC'] = df[Config.COL_PAINT_TYPE].astype(str).str.contains(Config.SPC_PAINT_KEYWORD, case=False, na=False).astype(int)

    df['paint_performance_factor'] = 1.0
    mask_penalty = (df['is_SPC'] == 1) & (df['pct_idle_recent'] > Config.PAINT_PENALTY_THRESHOLD)
    df.loc[mask_penalty, 'paint_performance_factor'] = Config.PAINT_PENALTY_FACTOR

    df['paint_x_speed'] = df['paint_encoded'] * df[Config.COL_SPEED]

    df['accumulated_fouling_risk'] = df['pct_idle_recent'] * df['days_since_cleaning']

    return df

def calculate_theoretical_power(row):
    disp = row[Config.COL_DISPLACEMENT]
    if pd.isna(disp) or disp == 0:
        disp = row[Config.COL_DRAFT] * Config.ADMIRALTY_SCALE_FACTOR

    speed = row[Config.COL_SPEED]
    # protect against NaN or very low speeds
    if pd.isna(speed) or speed < 1:
        return 0

    return (np.power(disp, 2/3) * np.power(speed, 3)) / Config.ADMIRALTY_SCALE_FACTOR

def get_days_since_cleaning_vectorized(df_events, df_drydock):
    """
    Vectorized calculation of days since last cleaning using merge_asof.
    Much faster than row-by-row apply for large datasets.
    """
    # Prepare drydock data: rename columns to match events, sort by date
    df_dock = df_drydock[[Config.COL_DOCAGEM_SHIP, Config.COL_DOCAGEM_DATE]].copy()
    df_dock = df_dock.rename(columns={
        Config.COL_DOCAGEM_SHIP: Config.COL_SHIP_NAME,
        Config.COL_DOCAGEM_DATE: 'last_dock_date'
    })
    df_dock = df_dock.sort_values('last_dock_date')

    # Prepare events: sort by ship and date
    df_ev = df_events[[Config.COL_SHIP_NAME, Config.COL_START_DATE]].copy()
    df_ev = df_ev.sort_values([Config.COL_SHIP_NAME, Config.COL_START_DATE])

    # merge_asof per ship: find last dock date <= event date
    results = []
    for ship in df_ev[Config.COL_SHIP_NAME].unique():
        ev_ship = df_ev[df_ev[Config.COL_SHIP_NAME] == ship].copy()
        dock_ship = df_dock[df_dock[Config.COL_SHIP_NAME] == ship].copy()
        if dock_ship.empty:
            ev_ship['last_dock_date'] = pd.NaT
        else:
            ev_ship = pd.merge_asof(
                ev_ship.sort_values(Config.COL_START_DATE),
                dock_ship.sort_values('last_dock_date'),
                left_on=Config.COL_START_DATE,
                right_on='last_dock_date',
                by=Config.COL_SHIP_NAME,
                direction='backward'
            )
        results.append(ev_ship)

    merged = pd.concat(results, ignore_index=True)
    merged['days_since_cleaning'] = (merged[Config.COL_START_DATE] - merged['last_dock_date']).dt.days
    return merged[[Config.COL_SHIP_NAME, Config.COL_START_DATE, 'days_since_cleaning']]

def generate_residual_analysis(y_true, y_pred, X_data, df_source):
    if len(y_true) < 10: return

    df_res = pd.DataFrame({
        'Real_Ratio': y_true,
        'Pred_Ratio': y_pred,
        'Error': y_true - y_pred,
        'DaysSinceCleaning': df_source.loc[X_data.index, 'days_since_cleaning']
    })

    print("\n" + "="*40)
    print("RESIDUAL ANALYSIS (TARGET: EXCESS RATIO)")
    print("="*40)

    df_res['days_bin'] = pd.cut(df_res['DaysSinceCleaning'], bins=[0, 90, 180, 365, 1000])
    print("\nAvg Prediction Error by Days Since Cleaning:")
    print(df_res.groupby('days_bin', observed=True)['Error'].mean())

def main():
    # Print all algorithm parameters at the start of execution
    print_algorithm_parameters()
    
    df_events, df_consumption, df_drydock, df_paint = load_data()

    df_events = feature_engineering_events(df_events)

    df_main = pd.merge(
        df_events,
        df_consumption,
        left_on=Config.COL_SESSION_ID,
        right_on=Config.COL_SESSION_ID_CONSUMPTION,
        how='inner'
    )

    df_paint = df_paint.drop_duplicates(subset=[Config.COL_SHIP_NAME])
    df_main = pd.merge(df_main, df_paint[[Config.COL_SHIP_NAME, Config.COL_PAINT_TYPE]], on=Config.COL_SHIP_NAME, how='left')
    df_main[Config.COL_PAINT_TYPE] = df_main[Config.COL_PAINT_TYPE].fillna('Generic')

    df_drydock = df_drydock.sort_values(Config.COL_DOCAGEM_DATE)
    # Vectorized days_since_cleaning (much faster than apply)
    days_df = get_days_since_cleaning_vectorized(df_main, df_drydock)
    df_main = pd.merge(df_main, days_df, on=[Config.COL_SHIP_NAME, Config.COL_START_DATE], how='left')

    df_main = df_main.dropna(subset=['days_since_cleaning', Config.COL_CONSUMPTION])
    df_main = df_main[df_main[Config.COL_CONSUMPTION] > Config.MIN_CONSUMPTION_THRESHOLD]

    Q1 = df_main[Config.COL_CONSUMPTION].quantile(0.01)
    Q3 = df_main[Config.COL_CONSUMPTION].quantile(0.99)
    df_main = df_main[(df_main[Config.COL_CONSUMPTION] >= Q1) & (df_main[Config.COL_CONSUMPTION] <= Q3)]

    df_main['theoretical_power_raw'] = df_main.apply(calculate_theoretical_power, axis=1)

    # --- EFFICIENCY CALIBRATION (per-ship or global) ---
    clean_ships = df_main[df_main['days_since_cleaning'] < 90].copy()
    clean_ships['power_duration'] = clean_ships['theoretical_power_raw'] * clean_ships[Config.COL_DURATION]
    clean_ships = clean_ships[clean_ships['power_duration'] > 0]  # avoid division by zero
    
    if Config.CALIBRATE_PER_SHIP:
        # Per-ship efficiency factor (more accurate baseline)
        efficiency_by_ship = (
            clean_ships.groupby(Config.COL_SHIP_NAME, as_index=True)['power_duration']
            .apply(lambda g: (clean_ships.loc[g.index, Config.COL_CONSUMPTION] / g).median())
        )
        # Simpler approach: calculate per ship directly
        efficiency_by_ship = clean_ships.groupby(Config.COL_SHIP_NAME).apply(
            lambda g: (g[Config.COL_CONSUMPTION] / g['power_duration']).median(),
            include_groups=False
        )
        # Global fallback for ships without clean data
        global_efficiency = (clean_ships[Config.COL_CONSUMPTION] / clean_ships['power_duration']).median()
        df_main['efficiency_factor'] = df_main[Config.COL_SHIP_NAME].map(efficiency_by_ship).fillna(global_efficiency)
        print(f"CALIBRATED EFFICIENCY FACTOR: per-ship (global fallback: {global_efficiency:.6f})")
        print(f"  Ships with individual calibration: {len(efficiency_by_ship)}")
    else:
        # Global efficiency factor (original behavior)
        global_efficiency = (clean_ships[Config.COL_CONSUMPTION] / clean_ships['power_duration']).median()
        df_main['efficiency_factor'] = global_efficiency
        print(f"CALIBRATED EFFICIENCY FACTOR: {global_efficiency:.6f}")

    df_main['baseline_consumption'] = df_main['theoretical_power_raw'] * df_main[Config.COL_DURATION] * df_main['efficiency_factor']

    df_main['target_excess_ratio'] = (df_main[Config.COL_CONSUMPTION] - df_main['baseline_consumption']) / df_main['baseline_consumption']

    df_main = df_main[(df_main['target_excess_ratio'] > -0.5) & (df_main['target_excess_ratio'] < 1.0)]

    # --- BIOFOULING INDEX, CLASSIFICATION, COST & EMISSIONS ---
    
    # (1) Dynamic BIO_REFERENCE from data if not set
    if Config.BIO_REFERENCE is None:
        bio_ref = df_main['target_excess_ratio'].quantile(Config.BIO_REFERENCE_PERCENTILE)
        bio_ref = max(bio_ref, 0.05)  # minimum 5% to avoid division issues
        print(f"DYNAMIC BIO_REFERENCE (P{int(Config.BIO_REFERENCE_PERCENTILE*100)}): {bio_ref:.4f} ({bio_ref*100:.1f}%)")
    else:
        bio_ref = Config.BIO_REFERENCE
        print(f"FIXED BIO_REFERENCE: {bio_ref:.4f} ({bio_ref*100:.1f}%)")
    
    # (2) Sigmoid or linear scale for bio_index
    if Config.USE_SIGMOID_SCALE:
        # Sigmoid function: smoother transition, avoids hard cutoffs
        # bio_index = 1 / (1 + exp(-k * (ER - midpoint)))
        k = Config.SIGMOID_K
        mid = Config.SIGMOID_MIDPOINT
        df_main['bio_index'] = 1 / (1 + np.exp(-k * (df_main['target_excess_ratio'] - mid)))
        df_main['bio_index'] = df_main['bio_index'].clip(lower=0, upper=1)
        print(f"SIGMOID SCALE: k={k}, midpoint={mid} (bio_index=0.5 at ER={mid*100:.0f}%)")
    else:
        # Linear scale (original behavior)
        df_main['bio_index'] = (df_main['target_excess_ratio'] / bio_ref).clip(lower=0, upper=1)
    
    df_main['bio_index_0_10'] = (df_main['bio_index'] * 10).round(1)

    # Qualitative classification (based on ER, not bio_index)
    def classify_bio(er):
        if pd.isna(er):
            return 'Unknown'
        if er < 0.10:
            return 'Leve'
        if er < 0.20:
            return 'Moderada'
        return 'Severa'

    df_main['bio_class'] = df_main['target_excess_ratio'].apply(classify_bio)

    # Cost and emissions estimates (only if fuel price provided)
    if Config.FUEL_PRICE_USD_PER_TON is not None:
        df_main['additional_fuel_tons'] = df_main['baseline_consumption'] * df_main['target_excess_ratio']
        df_main['additional_cost_usd'] = df_main['additional_fuel_tons'] * Config.FUEL_PRICE_USD_PER_TON
        df_main['additional_co2_tons'] = df_main['additional_fuel_tons'] * Config.CO2_TON_PER_FUEL_TON

    # Export a concise report CSV
    report_cols = [Config.COL_SHIP_NAME, Config.COL_START_DATE, Config.COL_SESSION_ID, Config.COL_CONSUMPTION,
                   'baseline_consumption', 'target_excess_ratio', 'bio_index_0_10', 'bio_class']
    if Config.FUEL_PRICE_USD_PER_TON is not None:
        report_cols += ['additional_fuel_tons', 'additional_cost_usd', 'additional_co2_tons']

    try:
        df_main[report_cols].to_csv(os.path.join(Config.DATA_PROCESSED_DIR, Config.REPORT_OUTPUT), index=False)
        print(f"Biofouling report exported to: {os.path.join(Config.DATA_PROCESSED_DIR, Config.REPORT_OUTPUT)}")
    except Exception as e:
        print(f"Failed to write biofouling report: {e}", file=sys.stderr)

    # --- (A) SUMMARY AGGREGATED BY SHIP ---
    summary_agg = {
        'target_excess_ratio': ['mean', 'max', 'count'],
        'bio_index_0_10': ['mean', 'max'],
        'baseline_consumption': 'sum',
        Config.COL_CONSUMPTION: 'sum'
    }
    if Config.FUEL_PRICE_USD_PER_TON is not None:
        summary_agg['additional_fuel_tons'] = 'sum'
        summary_agg['additional_cost_usd'] = 'sum'
        summary_agg['additional_co2_tons'] = 'sum'

    df_summary = df_main.groupby(Config.COL_SHIP_NAME).agg(summary_agg)
    df_summary.columns = ['_'.join(col).strip() for col in df_summary.columns.values]
    df_summary = df_summary.reset_index()
    # Rename for clarity
    df_summary = df_summary.rename(columns={
        'target_excess_ratio_mean': 'avg_excess_ratio',
        'target_excess_ratio_max': 'max_excess_ratio',
        'target_excess_ratio_count': 'num_events',
        'bio_index_0_10_mean': 'avg_bio_index',
        'bio_index_0_10_max': 'max_bio_index',
        'baseline_consumption_sum': 'total_baseline_fuel',
        f'{Config.COL_CONSUMPTION}_sum': 'total_real_fuel'
    })
    if Config.FUEL_PRICE_USD_PER_TON is not None:
        df_summary = df_summary.rename(columns={
            'additional_fuel_tons_sum': 'total_additional_fuel',
            'additional_cost_usd_sum': 'total_additional_cost_usd',
            'additional_co2_tons_sum': 'total_additional_co2'
        })
    try:
        df_summary.to_csv(os.path.join(Config.DATA_PROCESSED_DIR, Config.SUMMARY_OUTPUT), index=False)
        print(f"Ship summary exported to: {os.path.join(Config.DATA_PROCESSED_DIR, Config.SUMMARY_OUTPUT)}")
    except Exception as e:
        print(f"Failed to write ship summary: {e}", file=sys.stderr)

    le = LabelEncoder()
    df_main['paint_encoded'] = le.fit_transform(df_main[Config.COL_PAINT_TYPE].astype(str))

    df_main = feature_engineering_combined(df_main)
    df_main = df_main.sort_values(Config.COL_START_DATE)

    split_index = int(len(df_main) * Config.TRAIN_TEST_SPLIT_RATIO)
    df_train = df_main.iloc[:split_index]
    df_test = df_main.iloc[split_index:]

    features = [
        Config.COL_SPEED,
        'beaufortScale',
        'days_since_cleaning',
        'pct_idle_recent',
        'accumulated_fouling_risk',
        'historical_avg_speed',
        'paint_x_speed',
        'paint_encoded'
    ]

    X_train = df_train[features].copy()
    X_test = df_test[features].copy()

    numeric_cols = [f for f in features if f != 'paint_encoded']
    median_values = X_train[numeric_cols].median()
    X_train[numeric_cols] = X_train[numeric_cols].fillna(median_values)
    X_test[numeric_cols] = X_test[numeric_cols].fillna(median_values)

    X_train['paint_encoded'] = X_train['paint_encoded'].fillna(-1)
    X_test['paint_encoded'] = X_test['paint_encoded'].fillna(-1)

    y_train = df_train['target_excess_ratio']
    y_test = df_test['target_excess_ratio']

    validation_split_idx = int(len(X_train) * Config.VALIDATION_SPLIT_RATIO)
    X_fit = X_train.iloc[:validation_split_idx]
    y_fit = y_train.iloc[:validation_split_idx]
    X_val = X_train.iloc[validation_split_idx:]
    y_val = y_train.iloc[validation_split_idx:]

    model_params = Config.MODEL_PARAMS.copy()
    model = xgb.XGBRegressor(**model_params)

    model.fit(
        X_fit, y_fit,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    pred_ratio = model.predict(X_test)

    final_pred_consumption = df_test['baseline_consumption'] * (1 + pred_ratio)
    real_consumption = df_test[Config.COL_CONSUMPTION]

    rmse = np.sqrt(mean_squared_error(real_consumption, final_pred_consumption))
    mae = mean_absolute_error(real_consumption, final_pred_consumption)
    wmape = np.sum(np.abs(real_consumption - final_pred_consumption)) / np.sum(real_consumption)
    accuracy = 100 * (1 - wmape)

    print("-" * 40)
    print("FINAL RESULTS - BIOFOULING FOCUSED MODEL")
    print("-" * 40)
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"WMAPE: {wmape:.4%}")
    print(f"ACCURACY: {accuracy:.4f}%")
    print("-" * 40)

    importance = pd.DataFrame({
        'Feature': features,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)
    print("\nFEATURE IMPORTANCE (Deve ser dominado por Bio/Ops):")
    print(importance)

    generate_residual_analysis(y_test, pred_ratio, X_test, df_main)

    print("\n--- SANITY CHECK: BIOFOULING IMPACT ---")
    try:
        scenario = X_test.iloc[0:1].copy()
        baseline_val = df_test.iloc[0]['baseline_consumption']

        scen_clean = scenario.copy()
        scen_clean['days_since_cleaning'] = 30
        scen_clean['accumulated_fouling_risk'] = scen_clean['pct_idle_recent'] * 30
        pred_clean_ratio = model.predict(scen_clean)[0]
        fuel_clean = baseline_val * (1 + pred_clean_ratio)

        scen_dirty = scenario.copy()
        scen_dirty['days_since_cleaning'] = 400
        scen_dirty['accumulated_fouling_risk'] = scen_dirty['pct_idle_recent'] * 400
        pred_dirty_ratio = model.predict(scen_dirty)[0]
        fuel_dirty = baseline_val * (1 + pred_dirty_ratio)

        print(f"Baseline (Physics only): {baseline_val:.2f} tons")
        print(f"Prediction (Clean 30d):  {fuel_clean:.2f} tons (Ratio: {pred_clean_ratio:.2%})")
        print(f"Prediction (Dirty 400d): {fuel_dirty:.2f} tons (Ratio: {pred_dirty_ratio:.2%})")
        print(f"Biofouling Penalty: {fuel_dirty - fuel_clean:.2f} tons (+{((fuel_dirty/fuel_clean)-1)*100:.1f}%)")
    except Exception as e:
        print(f"Sanity Check Failed: {e}")

    joblib.dump(model, os.path.join(Config.MODELS_DIR, Config.MODEL_OUTPUT))
    joblib.dump(le, os.path.join(Config.MODELS_DIR, Config.ENCODER_OUTPUT))

if __name__ == "__main__":
    main()