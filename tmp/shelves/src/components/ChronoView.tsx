import React from 'react';
import { MediaItem } from '../data/mediaItems';

interface ChronoViewProps {
  items: MediaItem[];
  onItemClick: (item: MediaItem) => void;
}

const typeIcon: Record<string, string> = {
  music: '🎵',
  book: '📖',
  bd: '🎨',
};

const typeLabel: Record<string, string> = {
  music: 'Musique',
  book: 'Roman',
  bd: 'BD',
};

export const ChronoView: React.FC<ChronoViewProps> = ({ items, onItemClick }) => {
  const sorted = [...items].sort((a, b) => {
    const months: Record<string, number> = {
      Jan: 1, Fev: 2, Mar: 3, Avr: 4, Mai: 5, Juin: 6,
      Juil: 7, Aout: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12,
    };
    const parseDate = (d: string) => {
      const parts = d.split(' ');
      const day = parseInt(parts[0]);
      const month = months[parts[1]] || 1;
      const year = parseInt(parts[2]);
      return new Date(year, month - 1, day).getTime();
    };
    return parseDate(b.releaseDate) - parseDate(a.releaseDate);
  });

  return (
    <div className="space-y-3 px-2">
      {sorted.map((item, i) => (
        <div
          key={item.id}
          onClick={() => onItemClick(item)}
          className="group relative flex items-center gap-4 rounded-2xl p-4 cursor-pointer transition-all duration-300"
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.05)',
            animationDelay: `${i * 50}ms`,
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLDivElement;
            el.style.background = `${item.accentColor}0d`;
            el.style.borderColor = `${item.accentColor}33`;
            el.style.transform = 'translateX(4px)';
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLDivElement;
            el.style.background = 'rgba(255,255,255,0.02)';
            el.style.borderColor = 'rgba(255,255,255,0.05)';
            el.style.transform = 'translateX(0px)';
          }}
        >
          {/* Accent line */}
          <div
            className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full"
            style={{ background: item.accentColor, opacity: 0.6 }}
          />

          {/* Cover */}
          <div
            className="flex-shrink-0 rounded-lg overflow-hidden shadow-lg transition-transform duration-300 group-hover:scale-105"
            style={{
              width: item.type === 'music' ? 56 : item.type === 'book' ? 42 : 48,
              height: item.type === 'music' ? 56 : item.type === 'book' ? 63 : 64,
              boxShadow: `0 4px 16px rgba(0,0,0,0.5)`,
            }}
          >
            <img
              src={item.coverUrl}
              alt={item.title}
              className="w-full h-full object-cover"
            />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="text-[10px] font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded"
                style={{ background: `${item.accentColor}22`, color: item.accentColor }}
              >
                {typeIcon[item.type]} {typeLabel[item.type]}
              </span>
              {item.isNew && (
                <span
                  className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-sm"
                  style={{ background: item.accentColor, color: '#000' }}
                >
                  NEW
                </span>
              )}
            </div>
            <p className="text-white/85 text-sm font-semibold truncate leading-tight">{item.title}</p>
            <p className="text-white/40 text-xs truncate mt-0.5">{item.artist} · {item.publisher}</p>
          </div>

          {/* Right side */}
          <div className="flex-shrink-0 text-right">
            <p className="text-white/25 text-[10px] tabular-nums mb-1">{item.releaseDate}</p>
            <div
              className="flex items-center justify-end gap-1 text-[10px]"
              style={{ color: item.accentColor, opacity: 0.7 }}
            >
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                <path d="M2 6c0-2.21 1.79-4 4-4s4 1.79 4 4-1.79 4-4 4-4-1.79-4-4zm4-1v2l1.5 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>{item.rssSources.length} sources</span>
            </div>
          </div>

          {/* Hover arrow */}
          <div
            className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            style={{ color: item.accentColor }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
      ))}
    </div>
  );
};
