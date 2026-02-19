from rest_framework import serializers


class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class RoutePlanRequestSerializer(serializers.Serializer):
    start = CoordinateSerializer()
    end = CoordinateSerializer()


class FuelStopSerializer(serializers.Serializer):
    station_id = serializers.CharField()
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    distance_along_route_miles = serializers.FloatField()
    gallons_purchased = serializers.FloatField()
    cost_usd = serializers.FloatField()


class RoutePlanResponseSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_seconds = serializers.FloatField()
    geometry = serializers.ListField(
        child=CoordinateSerializer(),
        help_text="List of coordinates (lat/lng) representing the route polyline.",
    )
    fuel_stops = FuelStopSerializer(many=True)
    total_gallons = serializers.FloatField()
    total_cost_usd = serializers.FloatField()





