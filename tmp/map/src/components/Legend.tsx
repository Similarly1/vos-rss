import { CATEGORY_CONFIG, type NewsCategory } from "../data/newsData";

interface LegendProps {
  activeCategory: string | null;
  onCategoryToggle: (cat: NewsCategory | null) => void;
  counts: Record<string, number>;
}

export default function Legend({ activeCategory, onCategoryToggle, counts }: LegendProps) {
  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {(Object.keys(CATEGORY_CONFIG) as NewsCategory[])
        .filter((cat) => counts[cat] > 0)
        .map((cat) => {
          const cfg = CATEGORY_CONFIG[cat];
          const isActive = activeCategory === cat;
          const isFiltered = activeCategory !== null && !isActive;
          return (
            <button
              key={cat}
              onClick={() => onCategoryToggle(isActive ? null : cat)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
                border transition-all duration-200
                ${isActive
                  ? "text-white border-transparent shadow-lg scale-105"
                  : isFiltered
                  ? "text-slate-500 border-slate-700 bg-slate-900/40 opacity-50 hover:opacity-70"
                  : "text-slate-300 border-slate-700 bg-slate-900/60 hover:border-slate-500 hover:text-white"
                }
              `}
              style={isActive ? { backgroundColor: cfg.color, borderColor: cfg.color } : {}}
              aria-pressed={isActive}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: isActive ? "rgba(255,255,255,0.9)" : cfg.color }}
              />
              {cfg.label}
              <span
                className={`px-1.5 py-0.5 rounded-full text-xs font-bold
                  ${isActive ? "bg-white/20 text-white" : "bg-slate-800 text-slate-400"}`}
              >
                {counts[cat]}
              </span>
            </button>
          );
        })}
      {activeCategory && (
        <button
          onClick={() => onCategoryToggle(null)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                     text-slate-400 border border-slate-700 bg-slate-900/60
                     hover:text-white hover:border-slate-500 transition-all duration-200"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
          </svg>
          Tout afficher
        </button>
      )}
    </div>
  );
}
