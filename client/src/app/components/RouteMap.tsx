"use client";

import dynamic from "next/dynamic";
import { RoutePlanResponse } from "../types";

const RouteMapInner = dynamic(() => import("./RouteMapInner"), { ssr: false });

interface RouteMapProps {
  routeData: RoutePlanResponse | null;
}

export default function RouteMap({ routeData }: RouteMapProps) {
  return <RouteMapInner routeData={routeData} />;
}
