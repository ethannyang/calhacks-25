/**
 * Cooldown display component for tracking enemy ability cooldowns
 */

import { useCoachingStore } from '../store/coachingStore';

export default function CooldownDisplay() {
  const { enemyCooldowns } = useCoachingStore();

  if (!enemyCooldowns) {
    return null;
  }

  // Check if any cooldowns are active (> 0)
  const hasActiveCooldowns = Object.values(enemyCooldowns).some(cd => cd > 0);

  if (!hasActiveCooldowns) {
    return null;
  }

  return (
    <div className="fixed top-20 right-4 bg-black/70 backdrop-blur-sm rounded-lg p-3 shadow-lg border border-white/20">
      <div className="text-white/70 text-xs font-semibold mb-2">Enemy Cooldowns</div>
      <div className="flex gap-2">
        {(['Q', 'W', 'E', 'R'] as const).map((ability) => {
          const cooldown = enemyCooldowns[ability];
          const isOnCooldown = cooldown > 0;

          return (
            <div
              key={ability}
              className={`flex flex-col items-center justify-center w-12 h-12 rounded ${
                isOnCooldown
                  ? 'bg-red-500/30 border border-red-500/50'
                  : 'bg-green-500/30 border border-green-500/50'
              }`}
            >
              <div className="text-white font-bold text-sm">{ability}</div>
              {isOnCooldown ? (
                <div className="text-white text-xs">{Math.ceil(cooldown)}s</div>
              ) : (
                <div className="text-green-400 text-xs">✓</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
