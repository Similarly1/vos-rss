import { useEffect, useRef } from "react";
import { CATEGORY_CONFIG, type NewsItem } from "../data/newsData";

interface NewsPanelProps {
  news: NewsItem | null;
  onClose: () => void;
}

const RELIABILITY_LABELS: Record<string, { label: string; color: string }> = {
  high: { label: "Fiable", color: "text-green-400" },
  medium: { label: "Modéré", color: "text-amber-400" },
  low: { label: "Non vérifié", color: "text-red-400" },
};

export default function NewsPanel({ news, onClose }: NewsPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!news) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [news, onClose]);

  // Trap focus & scroll lock
  useEffect(() => {
    if (news) {
      document.body.style.overflow = "hidden";
      panelRef.current?.focus();
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [news]);

  if (!news) return null;

  const cfg = CATEGORY_CONFIG[news.category];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Side panel */}
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={news.title}
        className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-xl flex flex-col
                   bg-slate-950 shadow-2xl outline-none
                   border-l border-white/10
                   animate-slide-in"
        style={{ outline: "none" }}
      >
        {/* Hero image */}
        <div className="relative h-56 shrink-0 overflow-hidden">
          <img
            src={news.image}
            alt={news.title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/50 to-transparent" />

          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-9 h-9 flex items-center justify-center
                       rounded-full bg-slate-900/80 text-slate-300
                       hover:bg-slate-800 hover:text-white
                       border border-white/10 transition-all duration-200
                       focus:outline-none focus:ring-2 focus:ring-white/30"
            aria-label="Fermer"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>

          {/* Category badge */}
          <div className="absolute top-4 left-4">
            <span
              className="text-xs font-bold px-3 py-1 rounded-full text-white uppercase tracking-wider"
              style={{ backgroundColor: cfg.color }}
            >
              {cfg.label}
            </span>
          </div>

          {/* Title overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-5">
            <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <span>{news.location}</span>
              <span className="text-slate-600">•</span>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              <span>{new Date(news.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}</span>
            </div>
            <h2 className="text-white font-bold text-xl leading-tight">
              {news.title}
            </h2>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="p-6 space-y-6">

            {/* Stats bar */}
            <div className="flex items-center gap-4 py-3 px-4 rounded-xl bg-slate-900/60 border border-white/5">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <span className="font-semibold text-white">{news.views.toLocaleString("fr-FR")}</span>
                <span>lectures</span>
              </div>
              <div className="w-px h-4 bg-slate-700" />
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/>
                </svg>
                <span className="font-semibold text-white">{news.sources.length}</span>
                <span>sources citées</span>
              </div>
              <div className="w-px h-4 bg-slate-700" />
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-green-400 text-xs font-medium">En direct</span>
              </div>
            </div>

            {/* Summary */}
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
                Résumé
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed bg-slate-900/40 rounded-xl p-4 border border-white/5 italic">
                {news.summary}
              </p>
            </div>

            {/* Full content */}
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
                Analyse complète
              </h3>
              <div className="space-y-3">
                {news.fullContent.trim().split("\n\n").map((para, i) => (
                  <p key={i} className="text-slate-300 text-sm leading-relaxed">
                    {para}
                  </p>
                ))}
              </div>
            </div>

            {/* Tags */}
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
                Thématiques
              </h3>
              <div className="flex flex-wrap gap-2">
                {news.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs px-3 py-1 rounded-full border border-white/10 text-slate-300 bg-slate-800/60"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Sources */}
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
                Sources citées
              </h3>
              <div className="space-y-2">
                {news.sources.map((source, i) => {
                  const rel = RELIABILITY_LABELS[source.reliability];
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 rounded-xl
                                 bg-slate-900/60 border border-white/5
                                 hover:border-white/15 hover:bg-slate-800/60
                                 transition-all duration-200 group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-base border border-white/10">
                          {source.logo}
                        </div>
                        <div>
                          <p className="text-white text-sm font-medium">{source.name}</p>
                          <p className={`text-xs ${rel.color} flex items-center gap-1`}>
                            <span className="w-1.5 h-1.5 rounded-full inline-block"
                              style={{ backgroundColor: source.reliability === "high" ? "#4ade80" : source.reliability === "medium" ? "#fbbf24" : "#f87171" }}
                            />
                            {rel.label}
                          </p>
                        </div>
                      </div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300
                                   opacity-0 group-hover:opacity-100 transition-all duration-200"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Visiter
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                        </svg>
                      </a>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Bottom CTA */}
            <div className="pb-4">
              <div className="flex items-center gap-2 p-4 rounded-xl bg-slate-900/40 border border-white/5 text-slate-500 text-xs">
                <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span>Contenu agrégé de {news.sources.length} sources vérifiées. Les informations sont mises à jour régulièrement.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
