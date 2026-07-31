import { useState, useMemo } from "react";
import WorldMap from "./components/WorldMap";
import NewsPanel from "./components/NewsPanel";
import Legend from "./components/Legend";
import NewsTicker from "./components/NewsTicker";
import { NEWS_DATA, CATEGORY_CONFIG, type NewsItem, type NewsCategory } from "./data/newsData";

export default function App() {
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null);
  const [activeCategory, setActiveCategory] = useState<NewsCategory | null>(null);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    NEWS_DATA.forEach((n) => {
      counts[n.category] = (counts[n.category] || 0) + 1;
    });
    return counts;
  }, []);

  const handleCategoryToggle = (cat: NewsCategory | null) => {
    setActiveCategory(cat);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-white/5 bg-slate-950/90 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div>
              <h1 className="text-white font-bold text-base leading-none tracking-tight">
                WorldPulse
              </h1>
              <p className="text-slate-500 text-xs mt-0.5">Actualités croisées en temps réel</p>
            </div>
          </div>

          {/* Center stats */}
          <div className="hidden md:flex items-center gap-6">
            <div className="text-center">
              <div className="text-white font-bold text-lg leading-none">{NEWS_DATA.length}</div>
              <div className="text-slate-500 text-xs mt-0.5">Événements</div>
            </div>
            <div className="w-px h-8 bg-slate-800" />
            <div className="text-center">
              <div className="text-white font-bold text-lg leading-none">
                {NEWS_DATA.reduce((acc, n) => acc + n.sources.length, 0)}
              </div>
              <div className="text-slate-500 text-xs mt-0.5">Sources vérifiées</div>
            </div>
            <div className="w-px h-8 bg-slate-800" />
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-green-400 text-xs font-medium">Mise à jour continue</span>
            </div>
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/5 text-slate-400 text-xs">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              {new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" })}
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col">
        <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex-1 flex flex-col gap-5">

          {/* Legend / Filters */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-slate-200 font-semibold text-lg">
                Carte des actualités mondiales
              </h2>
              <p className="text-slate-500 text-sm mt-0.5">
                Survolez un marqueur pour un aperçu · Cliquez pour l'article complet
              </p>
            </div>
            <Legend
              activeCategory={activeCategory}
              onCategoryToggle={handleCategoryToggle}
              counts={categoryCounts}
            />
          </div>

          {/* Map */}
          <div className="rounded-2xl overflow-hidden border border-white/5 shadow-2xl flex-1 min-h-[400px]">
            <WorldMap
              onMarkerClick={setSelectedNews}
              activeCategory={activeCategory}
            />
          </div>

          {/* News grid */}
          <div>
            <h3 className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-3">
              {activeCategory
                ? `${CATEGORY_CONFIG[activeCategory].label} — ${categoryCounts[activeCategory]} événements`
                : "Tous les événements"}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {NEWS_DATA
                .filter((n) => !activeCategory || n.category === activeCategory)
                .map((news) => (
                  <NewsCard key={news.id} news={news} onClick={() => setSelectedNews(news)} />
                ))}
            </div>
          </div>
        </div>
      </main>

      {/* Ticker */}
      <NewsTicker />

      {/* Footer */}
      <footer className="shrink-0 border-t border-white/5 bg-slate-950 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-slate-600 text-xs">
          <p>© 2025 WorldPulse — Agrégateur d'actualités mondiales croisées</p>
          <p>Sources vérifiées · Données illustratives</p>
        </div>
      </footer>

      {/* Side panel */}
      <NewsPanel news={selectedNews} onClose={() => setSelectedNews(null)} />
    </div>
  );
}

function NewsCard({ news, onClick }: { news: NewsItem; onClick: () => void }) {
  const cfg = CATEGORY_CONFIG[news.category];
  return (
    <button
      onClick={onClick}
      className="group text-left rounded-xl overflow-hidden border border-white/5
                 bg-slate-900/60 hover:bg-slate-800/70 hover:border-white/10
                 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5
                 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
    >
      {/* Image */}
      <div className="relative h-28 overflow-hidden">
        <img
          src={news.image}
          alt={news.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 to-transparent" />
        <span
          className="absolute top-2 left-2 text-xs font-semibold px-2 py-0.5 rounded-full text-white"
          style={{ backgroundColor: cfg.color }}
        >
          {cfg.label}
        </span>
      </div>
      {/* Content */}
      <div className="p-3">
        <h4 className="text-white text-xs font-semibold leading-tight line-clamp-2 mb-1.5 group-hover:text-blue-300 transition-colors">
          {news.title}
        </h4>
        <div className="flex items-center justify-between">
          <span className="text-slate-600 text-xs">{news.location.split(",")[0]}</span>
          <div className="flex items-center gap-1">
            {news.sources.slice(0, 3).map((s, i) => (
              <span key={i} className="text-xs" title={s.name}>{s.logo}</span>
            ))}
            {news.sources.length > 3 && (
              <span className="text-slate-600 text-xs">+{news.sources.length - 3}</span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
