import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import * as d3 from "d3-geo";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import { NEWS_DATA, CATEGORY_CONFIG, type NewsItem } from "../data/newsData";

interface WorldMapProps {
  onMarkerClick: (news: NewsItem) => void;
  activeCategory: string | null;
}

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Singleton topo cache
let cachedTopo: Topology | null = null;

export default function WorldMap({ onMarkerClick, activeCategory }: WorldMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [topoData, setTopoData] = useState<Topology | null>(cachedTopo);
  const [dimensions, setDimensions] = useState({ width: 960, height: 520 });
  const [tooltip, setTooltip] = useState<{
    news: NewsItem;
    x: number;
    y: number;
    side: "left" | "right";
  } | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Responsive sizing via ResizeObserver
  useEffect(() => {
    const update = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = Math.max(340, Math.min(560, w * 0.54));
      setDimensions({ width: w, height: h });
    };
    update();
    const ro = new ResizeObserver(update);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Load TopoJSON once
  useEffect(() => {
    if (cachedTopo) {
      setTopoData(cachedTopo);
      return;
    }
    fetch(GEO_URL)
      .then((r) => r.json())
      .then((topo: Topology) => {
        cachedTopo = topo;
        setTopoData(topo);
      })
      .catch(console.error);
  }, []);

  // Build projection from dimensions
  const projection = useMemo(() => {
    return d3
      .geoNaturalEarth1()
      .scale((dimensions.width / 640) * 100)
      .translate([dimensions.width / 2, dimensions.height / 2]);
  }, [dimensions]);

  // Build SVG paths from topo + projection
  const geoPaths = useMemo(() => {
    if (!topoData) return [];
    const countries = feature(
      topoData,
      topoData.objects.countries as GeometryCollection
    );
    if (!("features" in countries)) return [];
    const pathGen = d3.geoPath().projection(projection);
    return (countries.features as GeoJSON.Feature[]).map(
      (f) => pathGen(f as GeoJSON.Feature<GeoJSON.Geometry>) ?? ""
    );
  }, [topoData, projection]);

  // Graticule path
  const graticulePath = useMemo(() => {
    const pathGen = d3.geoPath().projection(projection);
    return pathGen(d3.geoGraticule()()) ?? "";
  }, [projection]);

  // Sphere path for clip
  const spherePath = useMemo(() => {
    const pathGen = d3.geoPath().projection(projection);
    return pathGen({ type: "Sphere" }) ?? "";
  }, [projection]);

  // Filtered news
  const filteredNews = useMemo(
    () =>
      activeCategory
        ? NEWS_DATA.filter((n) => n.category === activeCategory)
        : NEWS_DATA,
    [activeCategory]
  );

  // Marker positions
  const markerPositions = useMemo(() => {
    return filteredNews
      .map((news) => {
        const pos = projection(news.coordinates);
        if (!pos) return null;
        return { news, x: pos[0], y: pos[1] };
      })
      .filter(Boolean) as { news: NewsItem; x: number; y: number }[];
  }, [filteredNews, projection]);

  const handleMarkerEnter = useCallback(
    (news: NewsItem, e: React.MouseEvent<SVGGElement>) => {
      if (tooltipTimer.current) clearTimeout(tooltipTimer.current);
      const rect = svgRef.current!.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const side = cx > dimensions.width * 0.62 ? "left" : "right";
      setHoveredId(news.id);
      setTooltip({ news, x: cx, y: cy, side });
    },
    [dimensions.width]
  );

  const handleMarkerLeave = useCallback(() => {
    tooltipTimer.current = setTimeout(() => {
      setTooltip(null);
      setHoveredId(null);
    }, 220);
  }, []);

  const keepTooltip = useCallback(() => {
    if (tooltipTimer.current) clearTimeout(tooltipTimer.current);
  }, []);

  const hideTooltip = useCallback(() => {
    tooltipTimer.current = setTimeout(() => {
      setTooltip(null);
      setHoveredId(null);
    }, 220);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full select-none" style={{ minHeight: 340 }}>
      {/* Loading skeleton */}
      {!topoData && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900 rounded-2xl">
          <div className="flex flex-col items-center gap-3 text-slate-500">
            <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <span className="text-sm">Chargement de la carte…</span>
          </div>
        </div>
      )}

      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="block w-full"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
      >
        <defs>
          <clipPath id="map-clip">
            <path d={spherePath} />
          </clipPath>
          <radialGradient id="ocean-radial" cx="50%" cy="40%" r="65%">
            <stop offset="0%" stopColor="#0c2340" />
            <stop offset="100%" stopColor="#040d1a" />
          </radialGradient>
          <linearGradient id="land-hover-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2d5a8e" />
            <stop offset="100%" stopColor="#1e3a5f" />
          </linearGradient>
          <filter id="glow-sm" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-lg" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Ocean */}
        <path d={spherePath} fill="url(#ocean-radial)" />

        {/* Graticule */}
        <path
          d={graticulePath}
          clipPath="url(#map-clip)"
          fill="none"
          stroke="rgba(148,163,184,0.06)"
          strokeWidth={0.5}
        />

        {/* Countries */}
        <g clipPath="url(#map-clip)">
          {geoPaths.map((d, i) => (
            <path
              key={i}
              d={d}
              fill="#163354"
              stroke="#0a1e35"
              strokeWidth={0.35}
              style={{ transition: "fill 0.15s" }}
              className="hover:fill-[#1e4a7a] cursor-default"
            />
          ))}
        </g>

        {/* Sphere border */}
        <path
          d={spherePath}
          fill="none"
          stroke="rgba(148,163,184,0.15)"
          strokeWidth={1}
        />

        {/* Markers */}
        {markerPositions.map(({ news, x, y }) => {
          const cfg = CATEGORY_CONFIG[news.category];
          const isHovered = hoveredId === news.id;

          return (
            <g
              key={news.id}
              transform={`translate(${x},${y})`}
              className="cursor-pointer"
              onMouseEnter={(e) => handleMarkerEnter(news, e)}
              onMouseLeave={handleMarkerLeave}
              onClick={() => onMarkerClick(news)}
            >
              {/* Outer pulse ring */}
              <circle fill={cfg.color} opacity={0} r={6}>
                <animate
                  attributeName="r"
                  values={isHovered ? "8;28;8" : "6;22;6"}
                  dur={isHovered ? "1.4s" : "2.2s"}
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.35;0;0.35"
                  dur={isHovered ? "1.4s" : "2.2s"}
                  repeatCount="indefinite"
                />
              </circle>

              {/* Mid pulse ring */}
              <circle fill={cfg.color} opacity={0} r={4}>
                <animate
                  attributeName="r"
                  values={isHovered ? "5;18;5" : "4;14;4"}
                  dur={isHovered ? "1.4s" : "2.2s"}
                  begin="0.4s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.5;0;0.5"
                  dur={isHovered ? "1.4s" : "2.2s"}
                  begin="0.4s"
                  repeatCount="indefinite"
                />
              </circle>

              {/* Glow halo on hover */}
              {isHovered && (
                <circle
                  r={10}
                  fill={cfg.color}
                  opacity={0.25}
                  filter="url(#glow-lg)"
                />
              )}

              {/* Core marker */}
              <circle
                r={isHovered ? 8 : 6}
                fill={cfg.color}
                stroke="rgba(255,255,255,0.85)"
                strokeWidth={isHovered ? 2 : 1.5}
                filter="url(#glow-sm)"
                style={{ transition: "r 0.15s, stroke-width 0.15s" }}
              />

              {/* Inner dot */}
              <circle
                r={isHovered ? 3 : 2}
                fill="white"
                opacity={0.95}
                style={{ transition: "r 0.15s" }}
              />

              {/* Hover label */}
              {isHovered && (
                <g transform="translate(0, -16)">
                  <rect
                    x={-50}
                    y={-13}
                    width={100}
                    height={14}
                    rx={7}
                    fill="rgba(10,18,32,0.92)"
                    stroke={cfg.color}
                    strokeWidth={0.8}
                  />
                  <text
                    textAnchor="middle"
                    y={-3}
                    fill={cfg.color}
                    fontSize={7.5}
                    fontWeight={600}
                    letterSpacing={0.3}
                    fontFamily="system-ui, sans-serif"
                  >
                    {news.country.toUpperCase()}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Tooltip (HTML overlay for rich content) */}
      {tooltip && (
        <div
          className="pointer-events-auto absolute z-20"
          style={{
            left:
              tooltip.side === "right"
                ? Math.min(tooltip.x + 20, dimensions.width - 300)
                : "auto",
            right:
              tooltip.side === "left"
                ? Math.max(dimensions.width - tooltip.x + 20, 8)
                : "auto",
            top: Math.min(
              Math.max(tooltip.y - 24, 8),
              dimensions.height - 260
            ),
          }}
          onMouseEnter={keepTooltip}
          onMouseLeave={hideTooltip}
        >
          <TooltipCard news={tooltip.news} />
        </div>
      )}
    </div>
  );
}

function TooltipCard({ news }: { news: NewsItem }) {
  const cfg = CATEGORY_CONFIG[news.category];
  const formattedDate = new Date(news.date).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <div
      className="w-72 rounded-2xl overflow-hidden shadow-2xl border border-white/10 animate-fade-in"
      style={{
        background: "rgba(8, 16, 32, 0.97)",
        backdropFilter: "blur(16px)",
      }}
    >
      {/* Hero image */}
      <div className="relative h-36 overflow-hidden">
        <img
          src={news.image}
          alt={news.title}
          className="w-full h-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#08101f] via-[#08101f]/30 to-transparent" />

        {/* Category pill */}
        <div className="absolute top-2.5 left-2.5">
          <span
            className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full text-white"
            style={{ backgroundColor: cfg.color }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-white/70" />
            {cfg.label}
          </span>
        </div>

        {/* Location */}
        <div className="absolute bottom-2.5 left-2.5 right-2.5">
          <div className="flex items-center gap-1.5 text-slate-300 text-xs">
            <svg className="w-3 h-3 shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            <span className="truncate">{news.location}</span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-3.5">
        {/* Title */}
        <h3 className="font-bold text-white text-sm leading-snug mb-2">
          {news.title}
        </h3>

        {/* Summary — 2 sentences max */}
        <p className="text-slate-400 text-xs leading-relaxed"
          style={{
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {news.summary.split(". ").slice(0, 2).join(". ") + "."}
        </p>

        {/* Footer */}
        <div className="mt-3 flex items-center justify-between pt-2.5 border-t border-white/5">
          <div className="flex items-center gap-1.5">
            {/* Source logos */}
            {news.sources.slice(0, 3).map((s, i) => (
              <span key={i} className="text-sm" title={s.name}>{s.logo}</span>
            ))}
            <span className="text-slate-600 text-xs ml-1">{news.sources.length} sources</span>
          </div>
          <div className="flex items-center gap-1 text-blue-400 text-xs font-medium">
            <span>{formattedDate}</span>
          </div>
        </div>

        {/* Click hint */}
        <div className="mt-2 flex items-center gap-1.5 text-slate-600 text-xs">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5"/>
          </svg>
          Cliquez pour l'article complet
        </div>
      </div>
    </div>
  );
}
