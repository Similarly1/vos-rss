<script>
  export let item;
  export let index;
  export let onClick;

  let hovered = false;

  const dims = {
    music: { w: 124, h: 124 },
    book: { w: 92, h: 138 },
    bd: { w: 105, h: 140 },
    cinema: { w: 110, h: 145 },
  };
  const spineW = {
    music: 10,
    book: 16,
    bd: 12,
    cinema: 14,
  };

  $: d = (item && item.type && dims[item.type]) ? dims[item.type] : dims.cinema;
  $: sw = (item && item.type && spineW[item.type]) ? spineW[item.type] : 12;
  $: sign = index % 2 === 0 ? -1 : 1;
</script>

<div
  class="relative flex flex-col items-center cursor-pointer select-none outline-none"
  style="perspective: 900px; padding-bottom: 68px;"
  on:mouseenter={() => hovered = true}
  on:mouseleave={() => hovered = false}
  on:click={() => onClick(item)}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && onClick(item)}
  aria-label="{item.title} par {item.artist}"
>
  <!-- 3D object -->
  <div
    style="
      width: {d.w}px;
      height: {d.h}px;
      transform: {hovered ? 'rotateX(0deg) rotateY(0deg) translateY(-12px) scale(1.07)' : `rotateX(10deg) rotateY(${sign * 3}deg) translateY(0px) scale(1)`};
      transform-style: preserve-3d;
      transition: transform 0.38s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.38s ease;
      box-shadow: {hovered ? `0 28px 48px -8px rgba(0,0,0,0.85), 0 0 0 1px ${item.accentColor}44, 0 0 20px ${item.accentColor}22` : `0 10px 24px -4px rgba(0,0,0,0.65), 0 2px 6px rgba(0,0,0,0.4)`};
      position: relative;
      border-radius: {item.type === 'music' ? 4 : 2}px;
      overflow: visible;
    "
  >
    <!-- Inner flex layout (spine + cover) -->
    <div
      class="flex w-full h-full overflow-hidden"
      style="border-radius: {item.type === 'music' ? 4 : 2}px;"
    >
      <!-- Spine -->
      <div
        style="
          width: {sw}px;
          flex-shrink: 0;
          background: linear-gradient(180deg, {item.accentColor}66 0%, {item.color} 35%, #0a0a0a 100%);
          border-right: 1px solid rgba(255,255,255,0.06);
          position: relative;
          overflow: hidden;
        "
      >
        <div style="position: absolute; inset: 0; background: linear-gradient(90deg, rgba(255,255,255,0.07) 0%, transparent 100%);"></div>
      </div>

      <!-- Cover -->
      <div class="relative flex-1 overflow-hidden">
        <img
          src={item.coverUrl}
          alt={item.title}
          class="w-full h-full object-cover"
          style="
            filter: {hovered ? 'brightness(1.08) saturate(1.12) contrast(1.02)' : 'brightness(0.82) saturate(0.88)'};
            transition: filter 0.38s ease;
          "
          draggable="false"
        />

        <!-- Sheen -->
        <div
          style="
            position: absolute;
            inset: 0;
            background: {hovered ? 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, transparent 55%)' : 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, transparent 50%)'};
            transition: background 0.38s ease;
            pointer-events: none;
          "
        ></div>

        <!-- Bottom gradient -->
        <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 40%; background: linear-gradient(to top, rgba(0,0,0,0.55) 0%, transparent 100%); pointer-events: none;"></div>

        {#if item.isNew}
          <div style="position: absolute; top: 6px; right: 6px; background: {item.accentColor}; color: #000; font-size: 8px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; padding: 2px 5px; border-radius: 3px; line-height: 1.4;">
            NEW
          </div>
        {/if}

        {#if item.type === 'music'}
          <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; opacity: {hovered ? 0 : 0.55}; transition: opacity 0.3s ease; pointer-events: none;">
            <div style="width: 56px; height: 56px; border-radius: 50%; border: 2px solid {item.accentColor}88; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle, rgba(0,0,0,0.6) 25%, transparent 70%); box-shadow: 0 0 12px {item.accentColor}44;">
              <div style="width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.12);"></div>
            </div>
          </div>
        {/if}

        {#if item.type === 'bd'}
          <div style="position: absolute; bottom: 0; right: 0; width: 16px; height: 16px; background: linear-gradient(135deg, transparent 50%, rgba(0,0,0,0.5) 50%); pointer-events: none;"></div>
        {/if}
      </div>
    </div>

    {#if item.type === 'book' || item.type === 'bd'}
      <div style="position: absolute; right: -3px; top: 2px; bottom: 2px; width: 3px; background: linear-gradient(90deg, #2a2420, #1a1210); border-radius: 0 2px 2px 0; opacity: 0.7;"></div>
    {/if}
  </div>

  <!-- Shadow -->
  <div
    style="
      width: {d.w * 0.8}px;
      height: 8px;
      background: rgba(0,0,0,0.65);
      filter: blur(6px);
      border-radius: 50%;
      opacity: {hovered ? 0.9 : 0.35};
      transform: {hovered ? 'scaleX(1.15) translateY(2px)' : 'scaleX(1)'};
      transition: opacity 0.38s ease, transform 0.38s ease;
      margin-top: 2px;
    "
  ></div>

  <!-- Tooltip -->
  <div
    style="
      position: absolute;
      bottom: {hovered ? 4 : -4}px;
      left: 50%;
      transform: translateX(-50%);
      opacity: {hovered ? 1 : 0};
      transition: opacity 0.22s ease, bottom 0.22s ease;
      width: 168px;
      z-index: 30;
      pointer-events: none;
    "
  >
    <div style="position: absolute; top: -6px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 6px solid rgba(8,10,18,0.95);"></div>
    <div style="background: rgba(8,10,18,0.95); backdrop-filter: blur(16px); border: 1px solid {item.accentColor}33; border-radius: 10px; padding: 8px 12px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.6), 0 0 0 1px {item.accentColor}1a;">
      <p style="color: rgba(255,255,255,0.9); font-size: 11px; font-weight: 600; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{item.title}</p>
      <p style="color: rgba(255,255,255,0.42); font-size: 10px; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{item.artist || item.author}</p>
      <p style="color: {item.accentColor}; font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 4px;">{item.releaseDate}</p>
    </div>
  </div>
</div>
