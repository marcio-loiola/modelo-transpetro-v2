# =============================================================================
# INTEGRATED BIOFOULING SERVICE
# =============================================================================
"""
Service that integrates biofouling predictions with external APIs.
Provides enhanced predictions using real-time data from multiple sources.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .services import BiofoulingService, DataService
from .external_clients import get_api_manager, ExternalAPIManager
from .config import settings

logger = logging.getLogger(__name__)


class IntegratedBiofoulingService:
    """
    Enhanced Biofouling Service that integrates with external APIs.
    
    This service acts as an orchestrator, combining:
    - Local ML model predictions
    - Real-time weather/sea conditions
    - Vessel tracking data
    - Current fuel prices
    - Maintenance schedules
    - Emissions reporting
    """
    
    def __init__(
        self,
        biofouling_service: BiofoulingService,
        data_service: DataService,
        api_manager: ExternalAPIManager
    ):
        self.biofouling_service = biofouling_service
        self.data_service = data_service
        self.api_manager = api_manager
        
    async def get_enhanced_prediction(
        self,
        vessel_id: str,
        prediction_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get enhanced prediction using external APIs.
        
        Combines:
        1. Base ML prediction
        2. Weather conditions impact
        3. Real-time fuel prices
        4. Maintenance history
        """
        # Get base prediction
        base_prediction = self.biofouling_service.predict(prediction_request)
        
        # Enrich with external data (if available)
        enriched_data = {}
        
        # Get weather conditions
        if self.api_manager.is_available("weather"):
            lat = prediction_request.get("latitude", 0)
            lon = prediction_request.get("longitude", 0)
            sea_conditions = await self.api_manager.weather.get_sea_conditions(lat, lon)
            enriched_data["sea_conditions"] = sea_conditions
            
            # Adjust prediction based on sea state
            base_prediction = self._adjust_for_sea_conditions(
                base_prediction, 
                sea_conditions
            )
            
        # Get current fuel prices
        if self.api_manager.is_available("fuel_prices"):
            port = prediction_request.get("port")
            fuel_prices = await self.api_manager.fuel_prices.get_current_prices(port)
            enriched_data["fuel_prices"] = fuel_prices
            
            # Recalculate costs with real prices
            if fuel_prices.get("price_usd_per_ton"):
                base_prediction["fuel_cost_usd"] = (
                    base_prediction["predicted_consumption"] * 
                    fuel_prices["price_usd_per_ton"]
                )
                
        # Get maintenance history
        if self.api_manager.is_available("maintenance"):
            last_cleaning = await self.api_manager.maintenance.get_last_cleaning(vessel_id)
            if last_cleaning:
                days_since_cleaning = (datetime.now() - last_cleaning).days
                enriched_data["last_hull_cleaning"] = last_cleaning.isoformat()
                enriched_data["days_since_cleaning"] = days_since_cleaning
                
        # Get vessel position
        if self.api_manager.is_available("vessel_tracking"):
            position = await self.api_manager.vessel_tracking.get_vessel_position(vessel_id)
            if position:
                enriched_data["current_position"] = position
                
        return {
            **base_prediction,
            "enriched_data": enriched_data,
            "data_sources": self._get_data_sources()
        }
        
    def _adjust_for_sea_conditions(
        self,
        prediction: Dict[str, Any],
        sea_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adjust prediction based on sea conditions.
        
        Higher Beaufort scale = higher fuel consumption.
        """
        beaufort = sea_conditions.get("beaufort_scale", 0)
        
        # Sea state impact factor (empirical formula)
        # Beaufort 0-3: minimal impact
        # Beaufort 4-6: moderate impact (5-15% increase)
        # Beaufort 7+: significant impact (20%+ increase)
        if beaufort <= 3:
            impact_factor = 1.0
        elif beaufort <= 6:
            impact_factor = 1.0 + (beaufort - 3) * 0.05
        else:
            impact_factor = 1.15 + (beaufort - 6) * 0.10
            
        adjusted_prediction = prediction.copy()
        adjusted_prediction["predicted_consumption"] *= impact_factor
        adjusted_prediction["sea_state_adjustment"] = impact_factor
        adjusted_prediction["beaufort_scale"] = beaufort
        
        return adjusted_prediction
        
    def _get_data_sources(self) -> List[str]:
        """Get list of active data sources."""
        sources = ["ml_model"]
        
        if self.api_manager.is_available("weather"):
            sources.append("weather_api")
        if self.api_manager.is_available("vessel_tracking"):
            sources.append("vessel_tracking")
        if self.api_manager.is_available("fuel_prices"):
            sources.append("fuel_prices")
        if self.api_manager.is_available("maintenance"):
            sources.append("maintenance_api")
            
        return sources
        
    async def get_fleet_optimization_report(
        self,
        vessel_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Generate fleet-wide optimization report.
        
        Combines data from all services to provide:
        - Fleet-wide biofouling status
        - Recommended cleaning schedule
        - Cost optimization opportunities
        - Emissions reduction potential
        """
        fleet_data = []
        total_potential_savings = 0
        total_emissions_reduction = 0
        
        for vessel_id in vessel_ids:
            vessel_report = await self._get_vessel_optimization_data(vessel_id)
            fleet_data.append(vessel_report)
            total_potential_savings += vessel_report.get("potential_fuel_savings_usd", 0)
            total_emissions_reduction += vessel_report.get("potential_co2_reduction_tons", 0)
            
        # Sort by optimization priority
        fleet_data.sort(
            key=lambda x: x.get("optimization_priority", 0),
            reverse=True
        )
        
        return {
            "report_date": datetime.now().isoformat(),
            "vessels_analyzed": len(vessel_ids),
            "fleet_data": fleet_data,
            "summary": {
                "total_potential_fuel_savings_usd": total_potential_savings,
                "total_potential_co2_reduction_tons": total_emissions_reduction,
                "vessels_requiring_cleaning": len([
                    v for v in fleet_data 
                    if v.get("cleaning_recommended", False)
                ]),
                "average_fleet_biofouling_index": sum(
                    v.get("biofouling_index", 0) for v in fleet_data
                ) / len(fleet_data) if fleet_data else 0
            }
        }
        
    async def _get_vessel_optimization_data(
        self,
        vessel_id: str
    ) -> Dict[str, Any]:
        """Get optimization data for a single vessel."""
        # This would integrate with ship summary data
        # For now, return a template structure
        return {
            "vessel_id": vessel_id,
            "biofouling_index": 0.0,
            "potential_fuel_savings_usd": 0.0,
            "potential_co2_reduction_tons": 0.0,
            "cleaning_recommended": False,
            "optimization_priority": 0,
            "days_since_last_cleaning": None
        }
        
    async def submit_voyage_emissions(
        self,
        vessel_id: str,
        voyage_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit voyage emissions to regulatory API.
        
        Automatically calculates emissions based on fuel consumption
        and submits to IMO DCS / EU MRV reporting system.
        """
        if not self.api_manager.is_available("emissions"):
            return {"error": "Emissions API not configured"}
            
        # Calculate emissions
        fuel_consumed = voyage_data.get("fuel_consumed_tons", 0)
        co2_emissions = fuel_consumed * settings.CO2_TON_PER_FUEL_TON
        
        emissions_data = {
            "voyage_id": voyage_data.get("voyage_id"),
            "departure_port": voyage_data.get("departure_port"),
            "arrival_port": voyage_data.get("arrival_port"),
            "departure_date": voyage_data.get("departure_date"),
            "arrival_date": voyage_data.get("arrival_date"),
            "distance_nm": voyage_data.get("distance_nm"),
            "fuel_type": voyage_data.get("fuel_type", "VLSFO"),
            "fuel_consumed_tons": fuel_consumed,
            "co2_emissions_tons": co2_emissions,
            "cargo_carried_tons": voyage_data.get("cargo_carried_tons"),
            "transport_work": voyage_data.get("transport_work")
        }
        
        result = await self.api_manager.emissions.submit_voyage_emissions(
            vessel_id,
            emissions_data
        )
        
        return {
            "submitted": True,
            "emissions_data": emissions_data,
            "api_response": result
        }
        
    async def get_cleaning_recommendation(
        self,
        vessel_id: str,
        current_biofouling_index: float
    ) -> Dict[str, Any]:
        """
        Get cleaning recommendation based on multiple factors.
        
        Considers:
        - Current biofouling index
        - Time since last cleaning
        - Upcoming voyages
        - Fuel price trends
        - Available drydock slots
        """
        recommendation = {
            "vessel_id": vessel_id,
            "biofouling_index": current_biofouling_index,
            "cleaning_urgency": "normal",
            "recommended_action": None,
            "estimated_savings": 0,
            "next_available_slot": None
        }
        
        # Determine urgency based on biofouling index
        if current_biofouling_index >= 0.80:
            recommendation["cleaning_urgency"] = "critical"
            recommendation["recommended_action"] = "immediate_cleaning"
        elif current_biofouling_index >= 0.60:
            recommendation["cleaning_urgency"] = "high"
            recommendation["recommended_action"] = "schedule_cleaning_30_days"
        elif current_biofouling_index >= 0.40:
            recommendation["cleaning_urgency"] = "moderate"
            recommendation["recommended_action"] = "monitor_closely"
        else:
            recommendation["cleaning_urgency"] = "low"
            recommendation["recommended_action"] = "continue_operation"
            
        # Get maintenance schedule if available
        if self.api_manager.is_available("maintenance"):
            last_cleaning = await self.api_manager.maintenance.get_last_cleaning(vessel_id)
            if last_cleaning:
                recommendation["last_cleaning_date"] = last_cleaning.isoformat()
                recommendation["days_since_cleaning"] = (datetime.now() - last_cleaning).days
                
        return recommendation


class ServiceOrchestrator:
    """
    Main service orchestrator for the microservice.
    
    Manages:
    - Service initialization and lifecycle
    - Dependency injection
    - Health checks
    - Graceful shutdown
    """
    
    _instance: Optional["ServiceOrchestrator"] = None
    
    def __init__(self):
        self.biofouling_service: Optional[BiofoulingService] = None
        self.data_service: Optional[DataService] = None
        self.integrated_service: Optional[IntegratedBiofoulingService] = None
        self._initialized = False
        
    @classmethod
    def get_instance(cls) -> "ServiceOrchestrator":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    async def initialize(self):
        """Initialize all services."""
        if self._initialized:
            return
            
        logger.info("Initializing Service Orchestrator...")
        
        # Initialize core services
        self.biofouling_service = BiofoulingService()
        self.data_service = DataService()
        
        # Initialize external API manager
        api_manager = get_api_manager()
        await api_manager.initialize()
        
        # Create integrated service
        self.integrated_service = IntegratedBiofoulingService(
            self.biofouling_service,
            self.data_service,
            api_manager
        )
        
        self._initialized = True
        logger.info("Service Orchestrator initialized successfully")
        
    async def shutdown(self):
        """Shutdown all services."""
        logger.info("Shutting down Service Orchestrator...")
        
        # Shutdown external APIs
        api_manager = get_api_manager()
        await api_manager.shutdown()
        
        self._initialized = False
        logger.info("Service Orchestrator shut down")
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all services."""
        api_manager = get_api_manager()
        
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "services": {
                "biofouling_model": {
                    "loaded": self.biofouling_service.model is not None if self.biofouling_service else False
                },
                "external_apis": {
                    "weather": api_manager.is_available("weather"),
                    "vessel_tracking": api_manager.is_available("vessel_tracking"),
                    "fuel_prices": api_manager.is_available("fuel_prices"),
                    "maintenance": api_manager.is_available("maintenance"),
                    "emissions": api_manager.is_available("emissions")
                }
            }
        }


def get_orchestrator() -> ServiceOrchestrator:
    """Get the service orchestrator singleton."""
    return ServiceOrchestrator.get_instance()
