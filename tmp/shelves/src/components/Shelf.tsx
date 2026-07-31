import React from 'react';
import { MediaCard } from './MediaCard';
import { MediaItem, MediaType } from '../data/mediaItems';

interface ShelfProps {
  type: MediaType;
  items: MediaItem[];
  onItemClick: (item: MediaItem) => void;
  label: string;
  icon: string;
}

const shelfMeta: Record<MediaType, { emoji: string; color: string }> = {
  music: { emoji: '🎵', color: '#4f6ef7' },
  book: { emoji: '📖', color: '#f59e0b' },
  bd: { emoji: '🎨', color: '#e879f9' },
};

export const Shelf: React.FC<ShelfProps> = ({ type, items, onItemClick, label }) => {
  const meta = shelfMeta[type];

  return (
    <div className="mb-20 last:mb-4">
      {/* Section header */}
      <div className="flex items-center gap-3 mb-6 px-1">
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 7,
            padding: '4px 12px',
            borderRadius: 100,
            background: `${meta.color}16`,
            border: `1px solid ${meta.color}30`,
            color: meta.color,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
          }}
        >
          <span style={{ fontSize: 13 }}>{meta.emoji}</span>
          <span>{label}</span>
        </div>
        <div
          style={{
            flex: 1,
            height: 1,
            background: `linear-gradient(to right, ${meta.color}30, transparent)`,
          }}
        />
        <span style={{ color: 'rgba(255,255,255,0.18)', fontSize: 11 }}>
          {items.length} titres
        </span>
      </div>

      {/* Shelf structure with perspective */}
      <div style={{ perspective: '1400px', perspectiveOrigin: '50% 60%' }}>
        {/* Back wall of the shelf */}
        <div
          style={{
            background: `linear-gradient(180deg, rgba(8,8,12,0.6) 0%, rgba(14,14,20,0.8) 100%)`,
            borderRadius: '8px 8px 0 0',
            padding: '16px 20px 0 20px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Very subtle back wall texture */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundImage: `linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
                                linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)`,
              backgroundSize: '60px 60px',
              pointerEvents: 'none',
              opacity: 0.5,
            }}
          />
          {/* Left wall shadow */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              bottom: 0,
              width: 32,
              background: 'linear-gradient(to right, rgba(0,0,0,0.3), transparent)',
              pointerEvents: 'none',
            }}
          />
          {/* Right wall shadow */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              width: 32,
              background: 'linear-gradient(to left, rgba(0,0,0,0.3), transparent)',
              pointerEvents: 'none',
            }}
          />

          {/* Items row */}
          <div
            className="shelf-scroll"
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 18,
              paddingBottom: 8,
              overflowX: 'auto',
              position: 'relative',
              zIndex: 2,
            }}
          >
            {items.map((item, i) => (
              <div key={item.id} style={{ flexShrink: 0 }}>
                <MediaCard item={item} onClick={onItemClick} index={i} />
              </div>
            ))}
            {/* Spacer at end for scroll breathing room */}
            <div style={{ width: 20, flexShrink: 0 }} />
          </div>
        </div>

        {/* Shelf board */}
        <div
          style={{
            height: 16,
            marginLeft: -2,
            marginRight: -2,
            background: 'linear-gradient(180deg, #2e2824 0%, #1c1612 50%, #0e0b08 100%)',
            borderTop: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '0 6px 30px rgba(0,0,0,0.8), 0 2px 8px rgba(0,0,0,0.5)',
            position: 'relative',
          }}
        >
          {/* Shelf wood grain lines */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: `repeating-linear-gradient(
                90deg,
                transparent,
                transparent 120px,
                rgba(255,255,255,0.015) 120px,
                rgba(255,255,255,0.015) 121px
              )`,
            }}
          />
        </div>

        {/* Drop shadow under shelf */}
        <div
          style={{
            height: 12,
            marginLeft: 12,
            marginRight: 12,
            background: 'rgba(0,0,0,0.5)',
            filter: 'blur(10px)',
            transform: 'scaleY(0.4)',
            transformOrigin: 'top',
            marginTop: -4,
          }}
        />
      </div>
    </div>
  );
};
