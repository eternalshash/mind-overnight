import React, { useEffect, useRef } from 'react';

/**
 * Retro 90s Animated Ballon d'Or Component.
 * - Simulates 3D facet rotation using pixel-art canvas rendering.
 * - Pyrite crystal base & engraved brass plate.
 * - Sparkling shimmer traverse every 5 seconds.
 */
export default function BallonDor({ size = 260, interactive = true }) {
  const canvasRef = useRef(null);
  const rotationRef = useRef(0);
  const lastSparkleBurstRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Crisp pixel rendering
    ctx.imageSmoothingEnabled = false;

    let animId;
    let startTime = Date.now();

    const render = () => {
      const now = Date.now();
      const elapsed = now - startTime;

      // 3D Rotation angle (approx 30 RPM)
      rotationRef.current += 0.022;
      const angle = rotationRef.current;

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const cx = canvas.width / 2;
      const cy = 96;
      const radius = 56;

      // Every 5 seconds: sparkle shimmer phase (0 to 1 over 1.2 seconds)
      const shimmerCycle = (elapsed % 5000);
      const isShimmering = shimmerCycle < 1400;
      const shimmerProgress = isShimmering ? shimmerCycle / 1400 : -1;

      // 1. Draw Golden Sphere with Rotating 3D Facets
      // Base sphere shadow / aura
      const grad = ctx.createRadialGradient(cx - 15, cy - 15, 8, cx, cy, radius);
      grad.addColorStop(0, '#fff6a3');
      grad.addColorStop(0.2, '#ffd700');
      grad.addColorStop(0.6, '#c68b00');
      grad.addColorStop(0.9, '#7a4f00');
      grad.addColorStop(1, '#332000');

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#2b1b00';
      ctx.stroke();
      ctx.clip(); // Clip facets to sphere

      // Draw rotating longitude lines & facet seams
      const numLongitudes = 10;
      ctx.lineWidth = 1.5;
      for (let i = 0; i < numLongitudes; i++) {
        const phi = angle + (i * Math.PI) / (numLongitudes / 2);
        const cosPhi = Math.cos(phi);
        const sinPhi = Math.sin(phi);

        // Only draw visible hemisphere
        if (sinPhi > -0.15) {
          const xOffset = cosPhi * radius;
          ctx.beginPath();
          ctx.ellipse(cx, cy, Math.abs(xOffset), radius, 0, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(60, 38, 0, 0.55)';
          ctx.stroke();

          // Hexagonal facet patches along the longitude
          for (let lat = -2; lat <= 2; lat++) {
            const latY = cy + lat * 20;
            const patchRadius = Math.sqrt(Math.max(0, radius * radius - (latY - cy) * (latY - cy)));
            const patchX = cx + cosPhi * patchRadius;
            
            // Facet highlight based on lighting (light source top-left)
            const lightFactor = Math.max(0, -cosPhi * 0.7 + (lat < 0 ? 0.3 : -0.2));
            if (lightFactor > 0.35) {
              ctx.fillStyle = `rgba(255, 255, 220, ${lightFactor * 0.4})`;
              ctx.fillRect(Math.floor(patchX - 3), Math.floor(latY - 3), 6, 6);
            }
          }
        }
      }

      // Horizontal latitude seams
      [-32, -16, 0, 16, 32].forEach((latOffset) => {
        const rLat = Math.sqrt(radius * radius - latOffset * latOffset);
        ctx.beginPath();
        ctx.ellipse(cx, cy + latOffset, rLat, rLat * 0.28, 0, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(70, 45, 0, 0.4)';
        ctx.stroke();
      });

      // Shimmer sweep across facets
      if (shimmerProgress >= 0) {
        const sweepX = (cx - radius - 30) + shimmerProgress * (radius * 2 + 80);
        const shimmerGrad = ctx.createLinearGradient(sweepX - 25, cy - radius, sweepX + 25, cy + radius);
        shimmerGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
        shimmerGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.75)');
        shimmerGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = shimmerGrad;
        ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);
      }

      ctx.restore();

      // 2. Pyrite / Crystalline Rock Pedestal (Mineral block authentic to France Football trophy)
      const baseTopY = cy + radius - 4;
      const baseMidY = baseTopY + 28;
      const baseBottomY = baseMidY + 22;

      // Rugged crystal facets
      ctx.fillStyle = '#22232a';
      ctx.beginPath();
      ctx.moveTo(cx - 38, baseTopY);
      ctx.lineTo(cx + 38, baseTopY);
      ctx.lineTo(cx + 46, baseMidY);
      ctx.lineTo(cx + 52, baseBottomY);
      ctx.lineTo(cx - 52, baseBottomY);
      ctx.lineTo(cx - 46, baseMidY);
      ctx.closePath();
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#111215';
      ctx.stroke();

      // Crystal rock facet highlights
      const rockColors = ['#424654', '#343844', '#1f2129', '#5b6175'];
      const rockFacets = [
        [[cx - 36, baseTopY], [cx - 10, baseTopY], [cx - 16, baseMidY], [cx - 44, baseMidY]],
        [[cx - 10, baseTopY], [cx + 18, baseTopY], [cx + 12, baseMidY], [cx - 16, baseMidY]],
        [[cx + 18, baseTopY], [cx + 36, baseTopY], [cx + 44, baseMidY], [cx + 12, baseMidY]],
        [[cx - 44, baseMidY], [cx - 8, baseMidY], [cx - 14, baseBottomY], [cx - 50, baseBottomY]],
        [[cx - 8, baseMidY], [cx + 24, baseMidY], [cx + 18, baseBottomY], [cx - 14, baseBottomY]],
        [[cx + 24, baseMidY], [cx + 44, baseMidY], [cx + 50, baseBottomY], [cx + 18, baseBottomY]],
      ];

      rockFacets.forEach((poly, idx) => {
        ctx.fillStyle = rockColors[idx % rockColors.length];
        ctx.beginPath();
        ctx.moveTo(poly[0][0], poly[0][1]);
        for (let p = 1; p < poly.length; p++) {
          ctx.lineTo(poly[p][0], poly[p][1]);
        }
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = '#14161d';
        ctx.stroke();
      });

      // 3. Polished Brass / Gold Plinth Base Plate
      const plinthTopY = baseBottomY;
      const plinthHeight = 22;
      const plinthWidth = 124;

      const brassGrad = ctx.createLinearGradient(cx - plinthWidth / 2, plinthTopY, cx + plinthWidth / 2, plinthTopY);
      brassGrad.addColorStop(0, '#755106');
      brassGrad.addColorStop(0.2, '#ffd700');
      brassGrad.addColorStop(0.5, '#fff494');
      brassGrad.addColorStop(0.8, '#d49600');
      brassGrad.addColorStop(1, '#573b02');

      ctx.fillStyle = brassGrad;
      ctx.fillRect(cx - plinthWidth / 2, plinthTopY, plinthWidth, plinthHeight);
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#2b1b00';
      ctx.strokeRect(cx - plinthWidth / 2, plinthTopY, plinthWidth, plinthHeight);

      // Engraved Plaque Text
      ctx.fillStyle = '#1c1200';
      ctx.font = 'bold 7px "Courier New", monospace';
      ctx.textAlign = 'center';
      ctx.fillText("BALLON D'OR", cx, plinthTopY + 10);
      ctx.font = '6px "Courier New", monospace';
      ctx.fillStyle = '#3a2500';
      ctx.fillText("FRANCE FOOTBALL", cx, plinthTopY + 18);

      // 4. Sparkling Pixel Stars during Shimmer & Click Burst
      const drawPixelStar = (sx, sy, starScale = 1, brightness = 1) => {
        ctx.fillStyle = `rgba(255, 255, 255, ${brightness})`;
        const s = Math.round(2 * starScale);
        // Center
        ctx.fillRect(sx - s, sy - s, s * 2, s * 2);
        // Rays
        ctx.fillRect(sx - s * 3, sy - Math.floor(s / 2), s * 6, s);
        ctx.fillRect(sx - Math.floor(s / 2), sy - s * 3, s, s * 6);
        // Warm gold halo
        ctx.fillStyle = `rgba(255, 215, 0, ${brightness * 0.6})`;
        ctx.fillRect(sx - s * 2, sy - s * 2, s * 4, s * 4);
      };

      if (isShimmering) {
        // Compute 3 sparkle positions synchronized with shimmer progress
        const sparkTime = shimmerProgress * Math.PI;
        const sparkIntensity = Math.sin(sparkTime);

        if (shimmerProgress > 0.15 && shimmerProgress < 0.85) {
          drawPixelStar(cx - 28 + shimmerProgress * 30, cy - 35 + Math.sin(shimmerProgress * 4) * 20, 1.2, sparkIntensity);
        }
        if (shimmerProgress > 0.35 && shimmerProgress < 0.95) {
          drawPixelStar(cx + 10 + (shimmerProgress - 0.35) * 35, cy - 10, 0.9, sparkIntensity);
        }
        if (shimmerProgress > 0.5) {
          drawPixelStar(cx - 15, cy + 25, 1.0, sparkIntensity);
        }
      }

      // Extra burst if user clicked
      if (now - lastSparkleBurstRef.current < 900) {
        const burstProgress = (now - lastSparkleBurstRef.current) / 900;
        const fade = 1 - burstProgress;
        drawPixelStar(cx - 38, cy - 20, 1.4, fade);
        drawPixelStar(cx + 38, cy - 25, 1.4, fade);
        drawPixelStar(cx, cy - 48, 1.6, fade);
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, []);

  const handleTrophyClick = () => {
    if (!interactive) return;
    rotationRef.current += 1.2;
    lastSparkleBurstRef.current = Date.now();
  };

  return (
    <div 
      className="relative flex flex-col items-center select-none cursor-pointer group"
      onClick={handleTrophyClick}
      title="Click to spin Ballon d'Or"
    >
      <canvas
        ref={canvasRef}
        width={size}
        height={size * 0.85}
        className="transition-transform duration-300 group-hover:scale-105"
        style={{
          imageRendering: 'pixelated',
          filter: 'drop-shadow(0 0 16px rgba(255, 215, 0, 0.35))'
        }}
      />
      <div className="text-[10px] text-yellow-400/70 font-mono tracking-widest mt-1 uppercase flex items-center gap-1">
        <span className="inline-block w-1.5 h-1.5 bg-yellow-400 rounded-full animate-ping" />
        <span>TROPHY ENGINE // 3D PIXEL SHIMMER</span>
      </div>
    </div>
  );
}
