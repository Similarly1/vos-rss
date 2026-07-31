import { useState, useMemo } from 'react';
import { mediaItems, MediaItem, MediaType } from './data/mediaItems';
import { Shelf } from './components/Shelf';
import { DetailDrawer } from './components/DetailDrawer';
import { ChronoView } from './components/ChronoView';

type NavMode = 'news' | 'culture' | 'map';
type ViewMode = 'shelves' | 'chrono';

const navItems: { id: NavMode; icon: string; label: string }[] = [
  { id: 'news', icon: '📰', label: 'News' },
  { id: 'culture', icon: '🎨', label: 'Culture' },
  { id: 'map', icon: '🌍', label: 'Carte' },
];

const shelfConfig: { type: MediaType; label: string }[] = [
  { type: 'music', label: 'CD & Vinyle' },
  { type: 'book', label: 'Romans & Essais' },
  { type: 'bd', label: 'BD & Comics' },
];

function App() {
  const [navMode, setNavMode] = useState<NavMode>('culture');
  const [viewMode, setViewMode] = useState<ViewMode>('shelves');
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);


  const filteredByType = useMemo(() => {
    return shelfConfig.map(({ type, label }) => ({
      type,
      label,
      items: mediaItems.filter((item) => item.type === type),
    }));
  }, []);

  const handleItemClick = (item: MediaItem) => {
    setSelectedItem(item);
  };

  const handleDrawerClose = () => {
    setSelectedItem(null);
  };

  return (
    <div
      className="min-h-screen text-white"
      style={{
        background: 'linear-gradient(160deg, #0a0c14 0%, #080a10 50%, #06080f 100%)',
        fontFamily: "'Inter', system-ui, sans-serif",
      }}
    >
      {/* ── HEADER ────────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 flex items-center justify-between px-6 md:px-10 py-4"
        style={{
          background: 'rgba(8,10,16,0.85)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        {/* Logo + Title */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold"
              style={{
                background: 'linear-gradient(135deg, #4f6ef7, #a855f7)',
                boxShadow: '0 0 16px rgba(79,110,247,0.4)',
              }}
            >
              V
            </div>
            <span
              className="text-lg font-semibold tracking-tight"
              style={{ letterSpacing: '-0.02em', color: 'rgba(255,255,255,0.9)' }}
            >
              Vos
            </span>
          </div>
          <div
            className="hidden md:block w-px h-5 mx-1"
            style={{ background: 'rgba(255,255,255,0.1)' }}
          />
          <div className="hidden md:block">
            <h1
              className="text-xl font-bold tracking-tight"
              style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                background: 'linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.6) 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              Perspectives
            </h1>
          </div>
        </div>

        {/* Center subtitle (hidden on mobile) */}
        <div className="hidden lg:block text-center">
          <p className="text-white/25 text-xs tracking-widest uppercase">
            Bibliotheque culturelle — Dernieres sorties
          </p>
        </div>

        {/* Nav mode selector */}
        <nav
          className="flex items-center gap-1 rounded-full p-1"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          {navItems.map((nav) => (
            <button
              key={nav.id}
              onClick={() => setNavMode(nav.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200"
              style={{
                background: navMode === nav.id ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: navMode === nav.id ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.3)',
                border: navMode === nav.id ? '1px solid rgba(255,255,255,0.12)' : '1px solid transparent',
              }}
            >
              <span className="text-sm">{nav.icon}</span>
              <span className="hidden sm:inline">{nav.label}</span>
            </button>
          ))}
        </nav>
      </header>

      {/* ── PAGE TITLE (mobile) ───────────────────────────────────────── */}
      <div className="md:hidden px-6 pt-6 pb-2">
        <h1
          className="text-2xl font-bold"
          style={{
            fontFamily: "'Playfair Display', Georgia, serif",
            background: 'linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.6) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          Perspectives
        </h1>
      </div>

      {/* ── MAIN CONTENT ─────────────────────────────────────────────── */}
      <main className="px-4 md:px-8 lg:px-14 pt-8 pb-24 relative z-10">
        {/* Non-culture nav placeholder */}
        {navMode !== 'culture' && (
          <div
            className="rounded-2xl p-12 mb-10 text-center flex flex-col items-center gap-4"
            style={{ background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.04)' }}
          >
            <div className="text-5xl mb-2">{navMode === 'news' ? '📰' : '🌍'}</div>
            <h2 className="text-white/50 text-lg font-semibold">
              {navMode === 'news' ? 'Flux Actualites' : 'Vue Cartographique'}
            </h2>
            <p className="text-white/25 text-sm max-w-md">
              {navMode === 'news'
                ? 'Le flux d\'actualites agrege sera disponible prochainement. Selectionnez Culture pour explorer la bibliotheque.'
                : 'La carte geographique des sources RSS est en cours de developpement.'}
            </p>
            <button
              onClick={() => setNavMode('culture')}
              className="mt-2 px-4 py-2 rounded-full text-xs font-semibold transition-all duration-200 hover:brightness-110"
              style={{ background: 'rgba(79,110,247,0.2)', border: '1px solid rgba(79,110,247,0.3)', color: '#4f6ef7' }}
            >
              Voir la Bibliotheque Culturelle
            </button>
          </div>
        )}

        {/* Controls bar — culture only */}
        {navMode === 'culture' && (<>
        <div className="flex items-center justify-between mb-10 flex-wrap gap-4">
          {/* Sub-title */}
          <div>
            <p className="text-white/50 text-sm">
              <span className="text-white/20 mr-2">9 sorties</span>
              Fevrier 2025
            </p>
          </div>

          {/* View toggle */}
          <div className="flex items-center gap-2">
            {/* View mode toggle */}
            <div
              className="flex items-center rounded-full p-0.5 gap-0.5"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.07)',
              }}
            >
              <button
                onClick={() => setViewMode('shelves')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200"
                style={{
                  background: viewMode === 'shelves' ? 'rgba(255,255,255,0.1)' : 'transparent',
                  color: viewMode === 'shelves' ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.3)',
                  border: viewMode === 'shelves' ? '1px solid rgba(255,255,255,0.1)' : '1px solid transparent',
                }}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="1" y="10" width="12" height="1.5" rx="0.5" fill="currentColor" opacity="0.8" />
                  <rect x="1" y="6.5" width="12" height="1.5" rx="0.5" fill="currentColor" opacity="0.6" />
                  <rect x="1" y="3" width="12" height="1.5" rx="0.5" fill="currentColor" opacity="0.4" />
                  <rect x="2" y="4.5" width="2" height="6" rx="0.5" fill="currentColor" />
                  <rect x="5" y="5" width="2" height="5.5" rx="0.5" fill="currentColor" />
                  <rect x="8" y="4" width="2" height="6.5" rx="0.5" fill="currentColor" />
                  <rect x="11" y="5.5" width="2" height="5" rx="0.5" fill="currentColor" />
                </svg>
                <span>Par type</span>
              </button>
              <button
                onClick={() => setViewMode('chrono')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200"
                style={{
                  background: viewMode === 'chrono' ? 'rgba(255,255,255,0.1)' : 'transparent',
                  color: viewMode === 'chrono' ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.3)',
                  border: viewMode === 'chrono' ? '1px solid rgba(255,255,255,0.1)' : '1px solid transparent',
                }}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M7 4.5V7l2 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Chronologique</span>
              </button>
            </div>
          </div>
        </div>

        {/* Content area */}
        {viewMode === 'shelves' ? (
          /* ─── SHELVES VIEW ─── */
          <div
            className="relative rounded-2xl overflow-hidden p-6 md:p-10"
            style={{
              background: 'linear-gradient(160deg, rgba(255,255,255,0.018) 0%, rgba(255,255,255,0.008) 100%)',
              border: '1px solid rgba(255,255,255,0.05)',
            }}
          >
            {/* Dot grid background */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                backgroundImage:
                  'radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)',
                backgroundSize: '28px 28px',
                maskImage: 'radial-gradient(ellipse 100% 100% at 50% 0%, black 0%, transparent 75%)',
                WebkitMaskImage: 'radial-gradient(ellipse 100% 100% at 50% 0%, black 0%, transparent 75%)',
              }}
            />
            {/* Room back wall gradient */}
            <div
              className="absolute inset-0 pointer-events-none rounded-2xl"
              style={{
                background:
                  'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(79,110,247,0.05) 0%, transparent 70%)',
              }}
            />

            {filteredByType.map(({ type, label, items }) => (
              <Shelf
                key={type}
                type={type}
                items={items}
                onItemClick={handleItemClick}
                label={label}
                icon=""
              />
            ))}
          </div>
        ) : (
          /* ─── CHRONO VIEW ─── */
          <div
            className="rounded-2xl p-6 md:p-8"
            style={{
              background: 'rgba(255,255,255,0.015)',
              border: '1px solid rgba(255,255,255,0.04)',
            }}
          >
            <div className="mb-6 flex items-center gap-2">
              <div
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ background: '#4f6ef7' }}
              />
              <span className="text-white/30 text-xs uppercase tracking-widest font-semibold">
                Fil chronologique recent
              </span>
            </div>
            <ChronoView items={mediaItems} onItemClick={handleItemClick} />
          </div>
        )}

        {/* Footer info */}
        <div className="mt-12 flex items-center justify-center gap-6 flex-wrap">
          {[
            { label: 'Musique', count: 3, color: '#4f6ef7' },
            { label: 'Romans', count: 3, color: '#f59e0b' },
            { label: 'BD & Comics', count: 3, color: '#e879f9' },
          ].map((stat) => (
            <div key={stat.label} className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: stat.color }} />
              <span className="text-white/25 text-xs">
                <span className="font-semibold" style={{ color: stat.color }}>{stat.count}</span>
                {' '}{stat.label}
              </span>
            </div>
          ))}
          <div
            className="h-3 w-px"
            style={{ background: 'rgba(255,255,255,0.08)' }}
          />
          <span className="text-white/15 text-xs">
            Mise a jour automatique via RSS
          </span>
        </div>
        </>)}
      </main>

      {/* ── DETAIL DRAWER ─────────────────────────────────────────────── */}
      <DetailDrawer item={selectedItem} onClose={handleDrawerClose} />

      {/* ── AMBIENT GLOW ──────────────────────────────────────────────── */}
      <div
        className="fixed pointer-events-none"
        style={{
          top: '20%',
          left: '10%',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(79,110,247,0.04) 0%, transparent 70%)',
          zIndex: 0,
        }}
      />
      <div
        className="fixed pointer-events-none"
        style={{
          bottom: '10%',
          right: '5%',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(168,85,247,0.04) 0%, transparent 70%)',
          zIndex: 0,
        }}
      />
    </div>
  );
}

export default App;
