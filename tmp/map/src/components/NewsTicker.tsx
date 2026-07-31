import { useEffect, useRef } from "react";
import { NEWS_DATA, CATEGORY_CONFIG } from "../data/newsData";

export default function NewsTicker() {
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    // Duplicate content for seamless loop
    el.innerHTML += el.innerHTML;
  }, []);

  return (
    <div className="relative overflow-hidden bg-slate-900/80 border-t border-white/5 py-2">
      <div className="absolute left-0 top-0 bottom-0 w-16 z-10 bg-gradient-to-r from-slate-950 to-transparent pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-16 z-10 bg-gradient-to-l from-slate-950 to-transparent pointer-events-none" />
      <div
        ref={trackRef}
        className="flex items-center gap-8 whitespace-nowrap"
        style={{
          animation: "ticker 40s linear infinite",
        }}
      >
        {NEWS_DATA.map((news) => {
          const cfg = CATEGORY_CONFIG[news.category];
          return (
            <div key={news.id} className="flex items-center gap-3 shrink-0">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: cfg.color }}
              />
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wide" style={{ color: cfg.color }}>
                {cfg.label}
              </span>
              <span className="text-slate-300 text-xs">{news.title}</span>
              <span className="text-slate-700 text-xs">·</span>
              <span className="text-slate-500 text-xs">{news.location}</span>
              <span className="text-slate-800 mx-2">|</span>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}
