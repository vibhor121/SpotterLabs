from __future__ import annotations

from typing import Any, Dict, List

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .fuel_data import iter_fuel_stations
from .fuel_optimizer import compute_fuel_plan
from .routing_api import RoutingAPIError, get_route
from .serializers import (
    FuelStopSerializer,
    RoutePlanRequestSerializer,
    RoutePlanResponseSerializer,
)


class RoutePlanView(APIView):
    """
    POST /api/route-plan/

    Request JSON:
    {
      "start": { "lat": 37.7749, "lng": -122.4194 },
      "end":   { "lat": 34.0522, "lng": -118.2437 }
    }

    Response JSON includes:
    - route geometry
    - fuel stops along the route with prices and gallons
    - total gallons and total cost
    """

    def post(self, request, *args, **kwargs) -> Response:
        serializer = RoutePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]

        try:
            route = get_route(
                (start["lat"], start["lng"]),
                (end["lat"], end["lng"]),
            )
        except RoutingAPIError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        stations = list(iter_fuel_stations())
        fuel_stops_plan = compute_fuel_plan(
            stations,
            route,
            vehicle_range_miles=float(settings.VEHICLE_RANGE_MILES),
            mpg=float(settings.VEHICLE_MPG),
        )

        # Prepare response payload
        geometry_payload: List[Dict[str, Any]] = [
            {"lat": pt.lat, "lng": pt.lng} for pt in route.geometry
        ]

        fuel_stops_payload: List[Dict[str, Any]] = []
        total_cost = 0.0
        total_gallons = 0.0
        for stop in fuel_stops_plan:
            total_cost += stop.cost_usd
            total_gallons += stop.gallons_purchased
            fuel_stops_payload.append(
                {
                    "station_id": stop.station.station_id,
                    "name": stop.station.name,
                    "latitude": stop.station.latitude,
                    "longitude": stop.station.longitude,
                    "price_per_gallon": stop.station.price_per_gallon,
                    "distance_along_route_miles": stop.distance_along_route_miles,
                    "gallons_purchased": stop.gallons_purchased,
                    "cost_usd": stop.cost_usd,
                }
            )

        response_data = {
            "distance_miles": route.distance_miles,
            "duration_seconds": route.duration_seconds,
            "geometry": geometry_payload,
            "fuel_stops": fuel_stops_payload,
            "total_gallons": total_gallons,
            "total_cost_usd": total_cost,
        }

        response_serializer = RoutePlanResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)






