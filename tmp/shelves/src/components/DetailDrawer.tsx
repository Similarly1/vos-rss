import React, { useEffect, useRef } from 'react';
import { MediaItem } from '../data/mediaItems';

interface DetailDrawerProps {
  item: MediaItem | null;
  onClose: () => void;
}

const typeLabel: Record<string, string> = {
  music: 'CD / Vinyle',
  book: 'Roman',
  bd: 'Bande Dessinee',
};

const typeIcon: Record<string, string> = {
  music: '🎵',
  book: '📖',
  bd: '🎨',
};

export const DetailDrawer: React.FC<DetailDrawerProps> = ({ item, onClose }) => {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  useEffect(() => {
    if (item) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [item]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 transition-all duration-500"
        style={{
          background: item ? 'rgba(0,0,0,0.6)' : 'rgba(0,0,0,0)',
          backdropFilter: item ? 'blur(4px)' : 'blur(0px)',
          pointerEvents: item ? 'auto' : 'none',
        }}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className="fixed top-0 right-0 h-full z-50 flex flex-col"
        style={{
          width: 'min(520px, 95vw)',
          background: 'linear-gradient(135deg, #0f1117 0%, #080c14 100%)',
          borderLeft: item ? `1px solid ${item.accentColor}22` : '1px solid transparent',
          boxShadow: item ? '-20px 0 60px rgba(0,0,0,0.7)' : 'none',
          transform: item ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.45s cubic-bezier(0.32,0.72,0,1), box-shadow 0.45s ease',
          overflowY: 'auto',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(255,255,255,0.1) transparent',
        }}
      >
        {item && (
          <>
            {/* Hero section */}
            <div className="relative overflow-hidden flex-shrink-0" style={{ minHeight: 280 }}>
              {/* Background blurred cover */}
              <div
                className="absolute inset-0"
                style={{
                  backgroundImage: `url(${item.coverUrl})`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  filter: 'blur(20px) brightness(0.3) saturate(1.4)',
                  transform: 'scale(1.1)',
                }}
              />
              <div
                className="absolute inset-0"
                style={{
                  background: `linear-gradient(to bottom, ${item.color}99 0%, rgba(8,12,20,0.95) 100%)`,
                }}
              />

              {/* Close button */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full transition-all duration-200 hover:scale-110"
                style={{
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.12)',
                  color: 'rgba(255,255,255,0.6)',
                }}
                aria-label="Fermer"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>

              {/* Content */}
              <div className="relative z-10 p-7 flex gap-5 items-end" style={{ minHeight: 280 }}>
                {/* Cover thumbnail */}
                <div
                  className="flex-shrink-0 rounded-md overflow-hidden shadow-2xl"
                  style={{
                    width: item.type === 'music' ? 120 : item.type === 'book' ? 90 : 100,
                    height: item.type === 'music' ? 120 : item.type === 'book' ? 135 : 133,
                    boxShadow: `0 16px 40px rgba(0,0,0,0.7), 0 0 0 1px ${item.accentColor}33`,
                    transform: 'perspective(400px) rotateY(-6deg)',
                  }}
                >
                  <img
                    src={item.coverUrl}
                    alt={item.title}
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Title block */}
                <div className="flex-1 min-w-0 pb-1">
                  <div
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-widest mb-3"
                    style={{
                      background: `${item.accentColor}22`,
                      border: `1px solid ${item.accentColor}44`,
                      color: item.accentColor,
                    }}
                  >
                    <span>{typeIcon[item.type]}</span>
                    <span>{typeLabel[item.type]}</span>
                    {item.isNew && (
                      <span
                        className="ml-1 px-1 rounded-sm text-[9px]"
                        style={{ background: item.accentColor, color: '#000' }}
                      >
                        NEW
                      </span>
                    )}
                  </div>
                  <h2
                    className="text-white font-bold leading-tight mb-1.5"
                    style={{ fontSize: 'clamp(18px, 4vw, 24px)', fontFamily: 'Playfair Display, serif' }}
                  >
                    {item.title}
                  </h2>
                  <p className="text-white/50 text-sm font-medium">{item.artist}</p>
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 p-7 space-y-7">
              {/* Metadata pills */}
              <div className="flex flex-wrap gap-2">
                {[
                  { label: 'Genre', value: item.genre },
                  { label: 'Editeur', value: item.publisher },
                  { label: 'Sortie', value: item.releaseDate },
                ].map((meta) => (
                  <div
                    key={meta.label}
                    className="px-3 py-1.5 rounded-lg text-xs"
                    style={{
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.08)',
                    }}
                  >
                    <span className="text-white/30 mr-1.5">{meta.label}</span>
                    <span className="text-white/70 font-medium">{meta.value}</span>
                  </div>
                ))}
              </div>

              {/* Divider */}
              <div
                className="h-px"
                style={{ background: 'linear-gradient(to right, rgba(255,255,255,0.08), transparent)' }}
              />

              {/* Synopsis */}
              <div>
                <h3 className="text-white/30 text-[10px] uppercase tracking-widest font-semibold mb-3">
                  Synopsis
                </h3>
                <p className="text-white/65 text-sm leading-relaxed">{item.synopsis}</p>
              </div>

              {/* Divider */}
              <div
                className="h-px"
                style={{ background: 'linear-gradient(to right, rgba(255,255,255,0.08), transparent)' }}
              />

              {/* RSS Sources */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-white/30 text-[10px] uppercase tracking-widest font-semibold">
                    Sources RSS
                  </h3>
                  <div
                    className="px-1.5 py-0.5 rounded text-[10px] font-semibold tabular-nums"
                    style={{ background: `${item.accentColor}22`, color: item.accentColor }}
                  >
                    {item.rssSources.length}
                  </div>
                </div>

                <div className="space-y-3">
                  {item.rssSources.map((source) => (
                    <div
                      key={source.id}
                      className="group rounded-xl p-4 transition-all duration-200 cursor-pointer"
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.06)',
                      }}
                      onMouseEnter={(e) => {
                        (e.currentTarget as HTMLDivElement).style.background = `${item.accentColor}0d`;
                        (e.currentTarget as HTMLDivElement).style.borderColor = `${item.accentColor}33`;
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.03)';
                        (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.06)';
                      }}
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-base leading-none flex-shrink-0">{source.favicon}</span>
                          <span
                            className="text-xs font-semibold truncate"
                            style={{ color: item.accentColor }}
                          >
                            {source.name}
                          </span>
                        </div>
                        <span className="text-white/25 text-[10px] flex-shrink-0 tabular-nums">{source.date}</span>
                      </div>
                      <p className="text-white/75 text-xs font-medium mb-1.5 leading-snug">{source.title}</p>
                      <p className="text-white/40 text-[11px] leading-relaxed">{source.excerpt}</p>

                      {/* Read link */}
                      <div className="mt-2.5 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-widest text-white/20 group-hover:text-white/40 transition-colors">
                        <span>Lire l'article</span>
                        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                          <path d="M1 7L7 1M7 1H3M7 1V5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom CTA */}
              <div className="pt-2">
                <button
                  className="w-full py-3 rounded-xl text-sm font-semibold transition-all duration-200 hover:brightness-110 hover:scale-[1.01]"
                  style={{
                    background: `linear-gradient(135deg, ${item.accentColor} 0%, ${item.accentColor}cc 100%)`,
                    color: '#000',
                    boxShadow: `0 4px 20px ${item.accentColor}44`,
                  }}
                >
                  Ouvrir dans le flux
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
};
