"use client";

import maplibregl, {
  type GeoJSONSource,
  type LngLatBoundsLike,
  type Map as MapLibreMap,
  type Marker,
} from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { AreaOfInterest, Position } from "@/lib/projects";

interface ProjectMapProps {
  aois: AreaOfInterest[];
  draft: Position[];
  drawing: boolean;
  onDraftChange: (positions: Position[]) => void;
}

const emptyCollection = {
  type: "FeatureCollection" as const,
  features: [],
};

export default function ProjectMap({
  aois,
  draft,
  drawing,
  onDraftChange,
}: ProjectMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const aoisRef = useRef(aois);
  const drawingRef = useRef(drawing);
  const draftRef = useRef(draft);
  const onDraftChangeRef = useRef(onDraftChange);

  useEffect(() => {
    aoisRef.current = aois;
    drawingRef.current = drawing;
    draftRef.current = draft;
    onDraftChangeRef.current = onDraftChange;
  }, [aois, draft, drawing, onDraftChange]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      center: [30.5, 26.8],
      zoom: 4.4,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");
    map.on("load", () => {
      map.addSource("saved-aois", { type: "geojson", data: emptyCollection });
      map.addLayer({
        id: "saved-aois-fill",
        type: "fill",
        source: "saved-aois",
        paint: { "fill-color": "#166b4f", "fill-opacity": 0.2 },
      });
      map.addLayer({
        id: "saved-aois-line",
        type: "line",
        source: "saved-aois",
        paint: { "line-color": "#166b4f", "line-width": 2 },
      });
      map.addSource("draft-aoi", { type: "geojson", data: emptyCollection });
      map.addLayer({
        id: "draft-aoi-fill",
        type: "fill",
        source: "draft-aoi",
        paint: { "fill-color": "#b9e45e", "fill-opacity": 0.3 },
      });
      map.addLayer({
        id: "draft-aoi-line",
        type: "line",
        source: "draft-aoi",
        paint: {
          "line-color": "#102721",
          "line-width": 3,
          "line-dasharray": [2, 1],
        },
      });
      updateSavedSource(map, aoisRef.current);
      updateDraftSource(map, draftRef.current);
    });
    map.on("click", (event) => {
      if (!drawingRef.current) return;
      onDraftChangeRef.current([
        ...draftRef.current,
        [event.lngLat.lng, event.lngLat.lat],
      ]);
    });
    mapRef.current = map;
    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    updateSavedSource(map, aois);
    if (aois.length > 0 && draft.length === 0) fitToAOIs(map, aois);
  }, [aois, draft.length]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    updateDraftSource(map, draft);
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = draft.map((position, index) => {
      const element = document.createElement("div");
      element.className = "vertexMarker";
      const marker = new maplibregl.Marker({ element, draggable: drawing })
        .setLngLat(position)
        .addTo(map);
      marker.on("dragend", () => {
        const next = [...draftRef.current];
        const location = marker.getLngLat();
        next[index] = [location.lng, location.lat];
        onDraftChangeRef.current(next);
      });
      return marker;
    });
  }, [draft, drawing]);

  return <div className={`projectMap ${drawing ? "isDrawing" : ""}`} ref={containerRef} />;
}

function updateSavedSource(map: MapLibreMap, aois: AreaOfInterest[]) {
  const source = map.getSource("saved-aois") as GeoJSONSource | undefined;
  source?.setData({
    type: "FeatureCollection",
    features: aois.map((aoi) => ({
      type: "Feature",
      id: aoi.id,
      properties: { id: aoi.id, name: aoi.name },
      geometry: aoi.geometry,
    })),
  });
}

function updateDraftSource(map: MapLibreMap, draft: Position[]) {
  const source = map.getSource("draft-aoi") as GeoJSONSource | undefined;
  if (!source) return;
  const geometry =
    draft.length >= 3
      ? {
          type: "Polygon" as const,
          coordinates: [[...draft, draft[0]]],
        }
      : draft.length >= 2
        ? { type: "LineString" as const, coordinates: draft }
        : null;
  source.setData(
    geometry
      ? {
          type: "Feature",
          properties: {},
          geometry,
        }
      : emptyCollection,
  );
}

function fitToAOIs(map: MapLibreMap, aois: AreaOfInterest[]) {
  const positions = aois.flatMap((aoi) => aoi.geometry.coordinates[0] ?? []);
  if (positions.length === 0) return;
  const bounds = positions.reduce(
    (current, position) => current.extend(position as Position),
    new maplibregl.LngLatBounds(positions[0] as Position, positions[0] as Position),
  );
  map.fitBounds(bounds as LngLatBoundsLike, { padding: 70, maxZoom: 12 });
}
