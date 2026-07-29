export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: number[][][];
}

export interface AreaOfInterest {
  id: string;
  project_id: string;
  name: string;
  geometry: PolygonGeometry;
  area_sq_km: number;
  created_at: string;
  updated_at: string;
}

export type Position = [number, number];
