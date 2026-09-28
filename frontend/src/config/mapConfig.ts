export type MapConfig = {
  provider: string;
  tileUrl: string;
  attribution: string;
  maxZoom: number;
  minZoom: number;
};

// No-key provider for development/fallback.
// Using CartoDB Voyager without key yields "API KEY REQUIRED" watermarks.
// OpenStreetMap public tiles block access (403) under load.
// Esri World Street Map allows basic usage without an API key.
export const FALLBACK_CONFIG: MapConfig = {
  provider: 'esri',
  tileUrl: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, iPC, NAVTEQ, USGS, Intermap, NRCAN, METI, TomTom, 2012',
  maxZoom: 18,
  minZoom: 3,
};

export function resolveMapConfig(): MapConfig {
  const provider = import.meta.env.VITE_MAP_PROVIDER;
  const apiKey = import.meta.env.VITE_MAP_API_KEY;
  const customUrl = import.meta.env.VITE_MAP_TILE_URL;
  const customAttribution = import.meta.env.VITE_MAP_ATTRIBUTION;

  // If a fully custom URL is provided and it doesn't contain a placeholder, use it.
  if (customUrl && !customUrl.includes('YOUR_CARTO_KEY')) {
    return {
      provider: 'custom',
      tileUrl: customUrl,
      attribution: customAttribution || '',
      maxZoom: 19,
      minZoom: 3,
    };
  }

  // If a provider is explicitly configured and an API key is provided
  if (provider === 'carto' && apiKey) {
    return {
      provider: 'carto',
      tileUrl: `https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${apiKey}`,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 19,
      minZoom: 3,
    };
  }

  if (provider === 'maptiler' && apiKey) {
    return {
      provider: 'maptiler',
      tileUrl: `https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=${apiKey}`,
      attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> contributors',
      maxZoom: 19,
      minZoom: 3,
    };
  }

  // Fallback to the no-key provider if configuration is missing or invalid.
  return FALLBACK_CONFIG;
}

export const mapConfig = resolveMapConfig();
