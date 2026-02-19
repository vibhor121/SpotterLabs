export interface LatLng {
  lat: number;
  lng: number;
}

export interface FuelStop {
  station_id: string;
  name: string;
  latitude: number;
  longitude: number;
  price_per_gallon: number;
  distance_along_route_miles: number;
  gallons_purchased: number;
  cost_usd: number;
}

export interface RoutePlanResponse {
  distance_miles: number;
  duration_seconds: number;
  geometry: LatLng[];
  fuel_stops: FuelStop[];
  total_gallons: number;
  total_cost_usd: number;
}
