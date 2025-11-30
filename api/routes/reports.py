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
        
        # Apply filters
        if ship_name:
            df = df[df['shipName'].str.upper().str.strip() == ship_name.upper().strip()]
        
        if start_date:
            df['startGMTDate'] = pd.to_datetime(df['startGMTDate'])
            df = df[df['startGMTDate'].dt.date >= start_date]
        
        if end_date:
            df['startGMTDate'] = pd.to_datetime(df['startGMTDate'])
            df = df[df['startGMTDate'].dt.date <= end_date]
        
        if min_bio_index is not None:
            df = df[df['bio_index_0_10'] >= min_bio_index]
        
        if bio_class:
            df = df[df['bio_class'] == bio_class.value]
        
        total = len(df)
        
        # Apply pagination
        df = df.iloc[offset:offset + limit]
        
        # Convert to response objects
        records = []
        for _, row in df.iterrows():
            records.append(BiofoulingReportItem(
                ship_name=row['shipName'],
                event_date=pd.to_datetime(row['startGMTDate']),
                session_id=str(row['sessionId']),
                consumption=float(row['CONSUMED_QUANTITY']),
                baseline_consumption=float(row['baseline_consumption']),
                excess_ratio=float(row['target_excess_ratio']),
                bio_index=float(row['bio_index_0_10']),
                bio_class=BiofoulingClass(row['bio_class']),
                additional_fuel_tons=float(row.get('additional_fuel_tons', 0)) if 'additional_fuel_tons' in row else None,
                additional_cost_usd=float(row.get('additional_cost_usd', 0)) if 'additional_cost_usd' in row else None,
                additional_co2_tons=float(row.get('additional_co2_tons', 0)) if 'additional_co2_tons' in row else None,
            ))
        
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
            return {"message": "No data available"}
        
        stats = {
            "total_records": len(df),
            "total_ships": df['shipName'].nunique(),
            "date_range": {
                "start": str(pd.to_datetime(df['startGMTDate']).min().date()),
                "end": str(pd.to_datetime(df['startGMTDate']).max().date())
            },
            "bio_index": {
                "mean": round(df['bio_index_0_10'].mean(), 2),
                "median": round(df['bio_index_0_10'].median(), 2),
                "std": round(df['bio_index_0_10'].std(), 2),
                "min": round(df['bio_index_0_10'].min(), 2),
                "max": round(df['bio_index_0_10'].max(), 2)
            },
            "excess_ratio": {
                "mean": round(df['target_excess_ratio'].mean() * 100, 2),
                "median": round(df['target_excess_ratio'].median() * 100, 2),
                "std": round(df['target_excess_ratio'].std() * 100, 2)
            },
            "classification_distribution": df['bio_class'].value_counts().to_dict()
        }
        
        # Add cost statistics if available
        if 'additional_cost_usd' in df.columns:
            stats["costs"] = {
                "total_additional_fuel_tons": round(df['additional_fuel_tons'].sum(), 2),
                "total_additional_cost_usd": round(df['additional_cost_usd'].sum(), 2),
                "total_additional_co2_tons": round(df['additional_co2_tons'].sum(), 2)
            }
        
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
            return {"ships": [], "message": "No data available"}
        
        high_risk = summary_df[summary_df['max_bio_index'] >= threshold].copy()
        high_risk = high_risk.sort_values('max_bio_index', ascending=False)
        
        ships = []
        for _, row in high_risk.iterrows():
            ships.append({
                "ship_name": row['shipName'],
                "max_bio_index": round(row['max_bio_index'], 1),
                "avg_bio_index": round(row['avg_bio_index'], 1),
                "avg_excess_ratio": round(row['avg_excess_ratio'] * 100, 1),
                "potential_savings_usd": round(row.get('total_additional_cost_usd', 0), 2),
                "recommendation": "Cleaning recommended" if row['max_bio_index'] >= 8 else "Monitor closely"
            })
        
        return {
            "threshold": threshold,
            "total_high_risk": len(ships),
            "ships": ships
        }
        
    except Exception as e:
        logger.error(f"Error getting high-risk ships: {e}")
        raise HTTPException(status_code=500, detail=str(e))
