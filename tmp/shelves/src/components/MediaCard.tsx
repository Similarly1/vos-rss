import React, { useState } from 'react';
import { MediaItem } from '../data/mediaItems';

interface MediaCardProps {
  item: MediaItem;
  onClick: (item: MediaItem) => void;
  index: number;
}

const dims = {
  music: { w: 124, h: 124 },
  book: { w: 92, h: 138 },
  bd: { w: 105, h: 140 },
};

const spineW = {
  music: 10,
  book: 16,
  bd: 12,
};

export const MediaCard: React.FC<MediaCardProps> = ({ item, onClick, index }) => {
  const [hovered, setHovered] = useState(false);
  const d = dims[item.type];
  const sw = spineW[item.type];
  const sign = index % 2 === 0 ? -1 : 1;

  return (
    <div
      className="relative flex flex-col items-center cursor-pointer select-none"
      style={{ perspective: '900px', paddingBottom: 68 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onClick(item)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick(item)}
      aria-label={`${item.title} par ${item.artist}`}
    >
      {/* ── 3D Book/CD/BD object ── */}
      <div
        style={{
          width: d.w,
          height: d.h,
          transform: hovered
            ? 'rotateX(0deg) rotateY(0deg) translateY(-12px) scale(1.07)'
            : `rotateX(10deg) rotateY(${sign * 3}deg) translateY(0px) scale(1)`,
          transformStyle: 'preserve-3d',
          transition: 'transform 0.38s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.38s ease',
          boxShadow: hovered
            ? `0 28px 48px -8px rgba(0,0,0,0.85), 0 0 0 1px ${item.accentColor}44, 0 0 20px ${item.accentColor}22`
            : `0 10px 24px -4px rgba(0,0,0,0.65), 0 2px 6px rgba(0,0,0,0.4)`,
          position: 'relative',
          borderRadius: item.type === 'music' ? 4 : 2,
          overflow: 'visible',
        }}
      >
        {/* Inner flex layout (spine + cover) */}
        <div
          className="flex w-full h-full overflow-hidden"
          style={{ borderRadius: item.type === 'music' ? 4 : 2 }}
        >
          {/* Spine */}
          <div
            style={{
              width: sw,
              flexShrink: 0,
              background: `linear-gradient(180deg,
                ${item.accentColor}66 0%,
                ${item.color} 35%,
                #0a0a0a 100%)`,
              borderRight: `1px solid rgba(255,255,255,0.06)`,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Spine gloss */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(90deg, rgba(255,255,255,0.07) 0%, transparent 100%)',
              }}
            />
          </div>

          {/* Cover */}
          <div className="relative flex-1 overflow-hidden">
            <img
              src={item.coverUrl}
              alt={item.title}
              className="w-full h-full object-cover"
              style={{
                filter: hovered
                  ? 'brightness(1.08) saturate(1.12) contrast(1.02)'
                  : 'brightness(0.82) saturate(0.88)',
                transition: 'filter 0.38s ease',
              }}
              draggable={false}
            />

            {/* Sheen */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: hovered
                  ? 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, transparent 55%)'
                  : 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, transparent 50%)',
                transition: 'background 0.38s ease',
                pointerEvents: 'none',
              }}
            />

            {/* Bottom gradient for readability */}
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: '40%',
                background: 'linear-gradient(to top, rgba(0,0,0,0.55) 0%, transparent 100%)',
                pointerEvents: 'none',
              }}
            />

            {/* NEW badge */}
            {item.isNew && (
              <div
                style={{
                  position: 'absolute',
                  top: 6,
                  right: 6,
                  background: item.accentColor,
                  color: '#000',
                  fontSize: 8,
                  fontWeight: 700,
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  padding: '2px 5px',
                  borderRadius: 3,
                  lineHeight: 1.4,
                }}
              >
                NEW
              </div>
            )}

            {/* Music: vinyl ring overlay */}
            {item.type === 'music' && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: hovered ? 0 : 0.55,
                  transition: 'opacity 0.3s ease',
                  pointerEvents: 'none',
                }}
              >
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: '50%',
                    border: `2px solid ${item.accentColor}88`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'radial-gradient(circle, rgba(0,0,0,0.6) 25%, transparent 70%)',
                    boxShadow: `0 0 12px ${item.accentColor}44`,
                  }}
                >
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: `rgba(255,255,255,0.18)`,
                      border: '1px solid rgba(255,255,255,0.12)',
                    }}
                  />
                </div>
              </div>
            )}

            {/* BD: page-fold corner */}
            {item.type === 'bd' && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 0,
                  right: 0,
                  width: 16,
                  height: 16,
                  background: `linear-gradient(135deg, transparent 50%, rgba(0,0,0,0.5) 50%)`,
                  pointerEvents: 'none',
                }}
              />
            )}
          </div>
        </div>

        {/* Book: page thickness on right edge */}
        {(item.type === 'book' || item.type === 'bd') && (
          <div
            style={{
              position: 'absolute',
              right: -3,
              top: 2,
              bottom: 2,
              width: 3,
              background: 'linear-gradient(90deg, #2a2420, #1a1210)',
              borderRadius: '0 2px 2px 0',
              opacity: 0.7,
            }}
          />
        )}
      </div>

      {/* ── Shadow on shelf ── */}
      <div
        style={{
          width: d.w * 0.8,
          height: 8,
          background: 'rgba(0,0,0,0.65)',
          filter: 'blur(6px)',
          borderRadius: '50%',
          opacity: hovered ? 0.9 : 0.35,
          transform: hovered ? 'scaleX(1.15) translateY(2px)' : 'scaleX(1)',
          transition: 'opacity 0.38s ease, transform 0.38s ease',
          marginTop: 2,
        }}
      />

      {/* ── Tooltip ── */}
      <div
        style={{
          position: 'absolute',
          bottom: hovered ? 4 : -4,
          left: '50%',
          transform: 'translateX(-50%)',
          opacity: hovered ? 1 : 0,
          transition: 'opacity 0.22s ease, bottom 0.22s ease',
          width: 168,
          zIndex: 30,
          pointerEvents: 'none',
        }}
      >
        {/* Up arrow */}
        <div
          style={{
            position: 'absolute',
            top: -6,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 0,
            height: 0,
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderBottom: `6px solid rgba(8,10,18,0.95)`,
          }}
        />
        <div
          style={{
            background: 'rgba(8,10,18,0.95)',
            backdropFilter: 'blur(16px)',
            border: `1px solid ${item.accentColor}33`,
            borderRadius: 10,
            padding: '8px 12px',
            textAlign: 'center',
            boxShadow: `0 8px 24px rgba(0,0,0,0.6), 0 0 0 1px ${item.accentColor}1a`,
          }}
        >
          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: 11, fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.title}
          </p>
          <p style={{ color: 'rgba(255,255,255,0.42)', fontSize: 10, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.artist}
          </p>
          <p style={{ color: item.accentColor, fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 4 }}>
            {item.releaseDate}
          </p>
        </div>
      </div>
    </div>
  );
};
