# =============================================================================
# API ROUTES - SHIPS
# =============================================================================
"""
Endpoints for ship data and management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import logging

from ..schemas import (
    ShipInfo,
    ShipList,
    ShipSummary,
    FleetSummary,
    BiofoulingReport,
    BiofoulingReportItem,
    BiofoulingClass,
)
from ..services import DataService, get_data_service
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ships", tags=["Ships"])


@router.get(
    "/",
    response_model=ShipList,
    summary="List all ships",
    description="Get a list of all ships in the fleet"
)
async def list_ships(
    service: DataService = Depends(get_data_service)
) -> ShipList:
    """
    Get list of all ships with basic information.
    """
    try:
        events = service.load_events()
        
        if events.empty:
            return ShipList(total=0, ships=[])
        
        ships = []
        for ship_name in events[settings.COL_SHIP_NAME].unique():
            ship_events = events[events[settings.COL_SHIP_NAME] == ship_name]
            
            ships.append(ShipInfo(
                ship_name=ship_name,
                total_events=len(ship_events),
                last_event_date=ship_events[settings.COL_START_DATE].max(),
                last_cleaning_date=None,  # Would need drydock data
                days_since_cleaning=None,
                paint_type=None
            ))
        
        return ShipList(total=len(ships), ships=ships)
        
    except Exception as e:
        logger.error(f"Error listing ships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{ship_name}",
    response_model=ShipInfo,
    summary="Get ship details",
    description="Get detailed information for a specific ship"
)
async def get_ship(
    ship_name: str,
    service: DataService = Depends(get_data_service)
) -> ShipInfo:
    """
    Get detailed information for a specific ship.
    """
    try:
        events = service.get_ship_events(ship_name)
        
        if events.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Ship '{ship_name}' not found"
            )
        
        return ShipInfo(
            ship_name=ship_name.upper().strip(),
            total_events=len(events),
            last_event_date=events[settings.COL_START_DATE].max(),
            last_cleaning_date=None,
            days_since_cleaning=None,
            paint_type=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ship {ship_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{ship_name}/summary",
    response_model=ShipSummary,
    summary="Get ship biofouling summary",
    description="Get biofouling statistics summary for a specific ship"
)
async def get_ship_summary(
    ship_name: str,
    service: DataService = Depends(get_data_service)
) -> ShipSummary:
    """
    Get biofouling summary statistics for a specific ship.
    """
    try:
        summary_df = service.get_ship_summary()
        
        if summary_df.empty:
            raise HTTPException(
                status_code=404,
                detail="Summary data not available"
            )
        
        ship_data = summary_df[
            summary_df['shipName'].str.upper().str.strip() == ship_name.upper().strip()
        ]
        
        if ship_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Summary for ship '{ship_name}' not found"
            )
        
        row = ship_data.iloc[0]
        
        return ShipSummary(
            ship_name=row['shipName'],
            num_events=int(row.get('num_events', 0)),
            avg_excess_ratio=float(row.get('avg_excess_ratio', 0)),
            max_excess_ratio=float(row.get('max_excess_ratio', 0)),
            avg_bio_index=float(row.get('avg_bio_index', 0)),
            max_bio_index=float(row.get('max_bio_index', 0)),
            total_baseline_fuel=float(row.get('total_baseline_fuel', 0)),
            total_real_fuel=float(row.get('total_real_fuel', 0)),
            total_additional_fuel=float(row.get('total_additional_fuel', 0)) if 'total_additional_fuel' in row else None,
            total_additional_cost_usd=float(row.get('total_additional_cost_usd', 0)) if 'total_additional_cost_usd' in row else None,
            total_additional_co2=float(row.get('total_additional_co2', 0)) if 'total_additional_co2' in row else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ship summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/fleet/summary",
    response_model=FleetSummary,
    summary="Get fleet summary",
    description="Get fleet-wide biofouling statistics"
)
async def get_fleet_summary(
    service: DataService = Depends(get_data_service)
) -> FleetSummary:
    """
    Get fleet-wide biofouling summary statistics.
    """
    try:
        summary_df = service.get_ship_summary()
        
        if summary_df.empty:
            raise HTTPException(
                status_code=404,
                detail="Summary data not available"
            )
        
        ships = []
        for _, row in summary_df.iterrows():
            ships.append(ShipSummary(
                ship_name=row['shipName'],
                num_events=int(row.get('num_events', 0)),
                avg_excess_ratio=float(row.get('avg_excess_ratio', 0)),
                max_excess_ratio=float(row.get('max_excess_ratio', 0)),
                avg_bio_index=float(row.get('avg_bio_index', 0)),
                max_bio_index=float(row.get('max_bio_index', 0)),
                total_baseline_fuel=float(row.get('total_baseline_fuel', 0)),
                total_real_fuel=float(row.get('total_real_fuel', 0)),
                total_additional_fuel=float(row.get('total_additional_fuel', 0)) if 'total_additional_fuel' in row else None,
                total_additional_cost_usd=float(row.get('total_additional_cost_usd', 0)) if 'total_additional_cost_usd' in row else None,
                total_additional_co2=float(row.get('total_additional_co2', 0)) if 'total_additional_co2' in row else None,
            ))
        
        # Calculate fleet totals
        total_events = sum(s.num_events for s in ships)
        fleet_avg_bio = sum(s.avg_bio_index * s.num_events for s in ships) / max(total_events, 1)
        fleet_additional_fuel = sum(s.total_additional_fuel or 0 for s in ships)
        fleet_additional_cost = sum(s.total_additional_cost_usd or 0 for s in ships)
        fleet_additional_co2 = sum(s.total_additional_co2 or 0 for s in ships)
        
        return FleetSummary(
            total_ships=len(ships),
            total_events=total_events,
            fleet_avg_bio_index=round(fleet_avg_bio, 2),
            fleet_total_additional_fuel=round(fleet_additional_fuel, 2),
            fleet_total_additional_cost_usd=round(fleet_additional_cost, 2),
            fleet_total_additional_co2=round(fleet_additional_co2, 2),
            ships=ships
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fleet summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
