# =============================================================================
# API ROUTES - REPORTS
# =============================================================================
"""
Endpoints for biofouling reports and analytics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, date
import pandas as pd
import io
import logging

from ..schemas import (
    BiofoulingReport,
    BiofoulingReportItem,
    BiofoulingClass,
)
from ..services import DataService, get_data_service
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/biofouling",
    response_model=BiofoulingReport,
    summary="Get biofouling report",
    description="Get the full biofouling report with optional filters"
)
async def get_biofouling_report(
    ship_name: Optional[str] = Query(None, description="Filter by ship name"),
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    min_bio_index: Optional[float] = Query(None, ge=0, le=10, description="Minimum bio index"),
    bio_class: Optional[BiofoulingClass] = Query(None, description="Filter by classification"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: DataService = Depends(get_data_service)
) -> BiofoulingReport:
    """
    Get biofouling report with optional filters.
    
    Supports filtering by:
    - Ship name
    - Date range
    - Minimum biofouling index
    - Biofouling classification
    """
    try:
        df = service.get_biofouling_report()
        
        if df.empty:
            return BiofoulingReport(total_records=0, records=[])
        
        # Apply filters safely
        if ship_name and 'shipName' in df.columns:
            df = df[df['shipName'].str.upper().str.strip() == ship_name.upper().strip()]
        
        if start_date and 'startGMTDate' in df.columns:
            try:
                df['startGMTDate'] = pd.to_datetime(df['startGMTDate'])
                df = df[df['startGMTDate'].dt.date >= start_date]
            except Exception as e:
                logger.warning(f"Error filtering by start_date: {e}")
        
        if end_date and 'startGMTDate' in df.columns:
            try:
                if 'startGMTDate' not in df.columns or df['startGMTDate'].dtype != 'datetime64[ns]':
                    df['startGMTDate'] = pd.to_datetime(df['startGMTDate'])
                df = df[df['startGMTDate'].dt.date <= end_date]
            except Exception as e:
                logger.warning(f"Error filtering by end_date: {e}")
        
        if min_bio_index is not None and 'bio_index_0_10' in df.columns:
            df = df[df['bio_index_0_10'] >= min_bio_index]
        
        if bio_class and 'bio_class' in df.columns:
            df = df[df['bio_class'] == bio_class.value]
        
        total = len(df)
        
        # Apply pagination
        df = df.iloc[offset:offset + limit]
        
        # Convert to response objects
        records = []
        for _, row in df.iterrows():
            try:
                # Safely get values with defaults
                ship_name_val = str(row.get('shipName', 'Unknown'))
                
                # Parse date safely
                try:
                    event_date = pd.to_datetime(row.get('startGMTDate', datetime.now()))
                except:
                    event_date = datetime.now()
                
                # Get other values with safe defaults
                session_id = str(row.get('sessionId', ''))
                consumption = float(row.get('CONSUMED_QUANTITY', 0))
                baseline_cons = float(row.get('baseline_consumption', consumption))
                excess_ratio = float(row.get('target_excess_ratio', 0))
                bio_index = float(row.get('bio_index_0_10', 0))
                
                # Parse bio class safely
                bio_class_str = str(row.get('bio_class', 'Unknown'))
                try:
                    bio_class_enum = BiofoulingClass(bio_class_str)
                except:
                    bio_class_enum = BiofoulingClass.UNKNOWN
                
                records.append(BiofoulingReportItem(
                    ship_name=ship_name_val,
                    event_date=event_date,
                    session_id=session_id,
                    consumption=consumption,
                    baseline_consumption=baseline_cons,
                    excess_ratio=excess_ratio,
                    bio_index=bio_index,
                    bio_class=bio_class_enum,
                    additional_fuel_tons=float(row.get('additional_fuel_tons', 0)) if 'additional_fuel_tons' in row.index else None,
                    additional_cost_usd=float(row.get('additional_cost_usd', 0)) if 'additional_cost_usd' in row.index else None,
                    additional_co2_tons=float(row.get('additional_co2_tons', 0)) if 'additional_co2_tons' in row.index else None,
                ))
            except Exception as e:
                logger.warning(f"Error converting row to report item: {e}")
                continue
        
        return BiofoulingReport(total_records=total, records=records)
        
    except Exception as e:
        logger.error(f"Error getting biofouling report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/biofouling/export",
    summary="Export biofouling report",
    description="Export biofouling report as CSV"
)
async def export_biofouling_report(
    ship_name: Optional[str] = Query(None, description="Filter by ship name"),
    service: DataService = Depends(get_data_service)
) -> StreamingResponse:
    """
    Export biofouling report as CSV file.
    """
    try:
        df = service.get_biofouling_report()
        
        if ship_name:
            df = df[df['shipName'].str.upper().str.strip() == ship_name.upper().strip()]
        
        # Convert to CSV
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        
        filename = f"biofouling_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/statistics",
    summary="Get statistics",
    description="Get overall biofouling statistics"
)
async def get_statistics(
    service: DataService = Depends(get_data_service)
) -> dict:
    """
    Get overall biofouling statistics for the fleet.
    """
    try:
        df = service.get_biofouling_report()
        summary_df = service.get_ship_summary()
        
        if df.empty:
            return {
                "message": "No data available",
                "total_records": 0,
                "total_ships": 0,
                "date_range": {"start": None, "end": None},
                "bio_index": {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0},
                "excess_ratio": {"mean": 0, "median": 0, "std": 0},
                "classification_distribution": {}
            }
        
        # Validate required columns - use available columns
        available_cols = df.columns.tolist()
        required_cols = ['shipName', 'startGMTDate', 'bio_index_0_10', 'target_excess_ratio', 'bio_class']
        missing_cols = [col for col in required_cols if col not in available_cols]
        if missing_cols:
            logger.warning(f"Missing columns in report data: {missing_cols}")
            # Continue anyway with available columns
        
        stats = {
            "total_records": len(df),
            "total_ships": df['shipName'].nunique() if 'shipName' in df.columns else 0,
        }
        
        # Date range
        if 'startGMTDate' in df.columns and len(df) > 0:
            try:
                dates = pd.to_datetime(df['startGMTDate'], errors='coerce')
                dates = dates.dropna()
                if len(dates) > 0:
                    stats["date_range"] = {
                        "start": str(dates.min().date()),
                        "end": str(dates.max().date())
                    }
                else:
                    stats["date_range"] = {"start": None, "end": None}
            except Exception as e:
                logger.warning(f"Error parsing dates: {e}")
                stats["date_range"] = {"start": None, "end": None}
        else:
            stats["date_range"] = {"start": None, "end": None}
        
        # Bio index statistics
        if 'bio_index_0_10' in df.columns and len(df) > 0:
            try:
                bio_col = pd.to_numeric(df['bio_index_0_10'], errors='coerce').dropna()
                if len(bio_col) > 0:
                    stats["bio_index"] = {
                        "mean": round(float(bio_col.mean()), 2),
                        "median": round(float(bio_col.median()), 2),
                        "std": round(float(bio_col.std()), 2) if bio_col.std() > 0 else 0,
                        "min": round(float(bio_col.min()), 2),
                        "max": round(float(bio_col.max()), 2)
                    }
                else:
                    stats["bio_index"] = {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
            except Exception as e:
                logger.warning(f"Error calculating bio_index stats: {e}")
                stats["bio_index"] = {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
        else:
            stats["bio_index"] = {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
        
        # Excess ratio statistics
        if 'target_excess_ratio' in df.columns and len(df) > 0:
            try:
                excess_col = pd.to_numeric(df['target_excess_ratio'], errors='coerce').dropna()
                if len(excess_col) > 0:
                    stats["excess_ratio"] = {
                        "mean": round(float(excess_col.mean() * 100), 2),
                        "median": round(float(excess_col.median() * 100), 2),
                        "std": round(float(excess_col.std() * 100), 2) if excess_col.std() > 0 else 0
                    }
                else:
                    stats["excess_ratio"] = {"mean": 0, "median": 0, "std": 0}
            except Exception as e:
                logger.warning(f"Error calculating excess_ratio stats: {e}")
                stats["excess_ratio"] = {"mean": 0, "median": 0, "std": 0}
        else:
            stats["excess_ratio"] = {"mean": 0, "median": 0, "std": 0}
        
        # Classification distribution
        if 'bio_class' in df.columns and len(df) > 0:
            try:
                stats["classification_distribution"] = df['bio_class'].value_counts().to_dict()
            except:
                stats["classification_distribution"] = {}
        else:
            stats["classification_distribution"] = {}
        
        # Add cost statistics if available
        if 'additional_cost_usd' in df.columns and len(df) > 0:
            try:
                stats["costs"] = {
                    "total_additional_fuel_tons": round(float(df['additional_fuel_tons'].fillna(0).sum()), 2),
                    "total_additional_cost_usd": round(float(df['additional_cost_usd'].fillna(0).sum()), 2),
                    "total_additional_co2_tons": round(float(df['additional_co2_tons'].fillna(0).sum()), 2)
                }
            except Exception as e:
                logger.warning(f"Error calculating cost stats: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/high-risk",
    summary="Get high-risk ships",
    description="Get ships with high biofouling risk that may need cleaning"
)
async def get_high_risk_ships(
    threshold: float = Query(7.0, ge=0, le=10, description="Bio index threshold"),
    service: DataService = Depends(get_data_service)
) -> dict:
    """
    Get ships with biofouling index above threshold.
    
    Useful for:
    - Maintenance planning
    - Cleaning prioritization
    - Cost-benefit analysis
    """
    try:
        summary_df = service.get_ship_summary()
        
        if summary_df.empty:
            return {
                "threshold": threshold,
                "total_high_risk": 0,
                "ships": [],
                "message": "No data available"
            }
        
        # Validate required columns
        if 'max_bio_index' not in summary_df.columns:
            logger.warning("Missing max_bio_index column in summary data")
            return {
                "threshold": threshold,
                "total_high_risk": 0,
                "ships": [],
                "message": "Summary data is incomplete. Missing max_bio_index column"
            }
        
        # Filter high risk ships
        try:
            max_bio_col = pd.to_numeric(summary_df['max_bio_index'], errors='coerce')
            high_risk = summary_df[max_bio_col >= threshold].copy()
            if len(high_risk) > 0:
                high_risk = high_risk.sort_values('max_bio_index', ascending=False)
        except Exception as e:
            logger.warning(f"Error filtering high risk ships: {e}")
            high_risk = pd.DataFrame()
        
        ships = []
        for _, row in high_risk.iterrows():
            try:
                max_bio = float(row.get('max_bio_index', 0)) if pd.notna(row.get('max_bio_index')) else 0
                avg_bio = float(row.get('avg_bio_index', 0)) if pd.notna(row.get('avg_bio_index')) else 0
                avg_excess = float(row.get('avg_excess_ratio', 0)) if pd.notna(row.get('avg_excess_ratio')) else 0
                savings = float(row.get('total_additional_cost_usd', 0)) if pd.notna(row.get('total_additional_cost_usd')) else 0
                
                ships.append({
                    "ship_name": str(row.get('shipName', 'Unknown')),
                    "max_bio_index": round(max_bio, 1),
                    "avg_bio_index": round(avg_bio, 1),
                    "avg_excess_ratio": round(avg_excess * 100, 1),
                    "potential_savings_usd": round(savings, 2),
                    "recommendation": "Cleaning recommended" if max_bio >= 8 else "Monitor closely"
                })
            except Exception as e:
                logger.warning(f"Error processing ship row: {e}")
                continue
        
        return {
            "threshold": threshold,
            "total_high_risk": len(ships),
            "ships": ships
        }
        
    except Exception as e:
        logger.error(f"Error getting high-risk ships: {e}")
        raise HTTPException(status_code=500, detail=str(e))
