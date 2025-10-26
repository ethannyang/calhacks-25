/**
 * DirectiveCard - Displays LLM-powered DirectiveV1 coaching with primary/backup/micro/timers
 */

import { DirectiveV1 } from '../store/coachingStore';

interface DirectiveCardProps {
  directive: DirectiveV1;
}

const priorityStyles = {
  critical: 'bg-gradient-to-br from-red-600/95 to-red-700/95 border-red-400 shadow-red-500/50',
  high: 'bg-gradient-to-br from-orange-600/90 to-orange-700/90 border-orange-400 shadow-orange-500/40',
  medium: 'bg-gradient-to-br from-blue-600/85 to-blue-700/85 border-blue-400 shadow-blue-500/30',
  low: 'bg-gradient-to-br from-gray-600/80 to-gray-700/80 border-gray-400 shadow-gray-500/20',
};

const priorityText = {
  critical: 'animate-pulse',
  high: '',
  medium: '',
  low: '',
};

export default function DirectiveCard({ directive }: DirectiveCardProps) {
  const styleClass = priorityStyles[directive.priority];
  const textClass = priorityText[directive.priority];

  // Get icon based on priority or use default
  const getIcon = () => {
    switch (directive.priority) {
      case 'critical': return '🚨';
      case 'high': return '⚡';
      case 'medium': return '📊';
      case 'low': return '💡';
      default: return '🎯';
    }
  };

  return (
    <div
      className={`${styleClass} ${textClass}
        rounded-lg border-2 shadow-2xl
        px-8 py-6 min-w-[600px] max-w-[1200px] w-fit
        transition-all duration-300 ease-in-out`}
    >
      <div className="space-y-2">
        {/* Header with icon and window */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-2xl">{getIcon()}</span>
          <span className="text-xs font-mono text-white/70 bg-black/30 px-2 py-0.5 rounded">
            {directive.primary.window}
          </span>
        </div>

        {/* Primary Directive */}
        <div className="border-l-4 border-white/40 pl-3 mb-3">
          <p className="text-white font-bold text-base leading-tight whitespace-pre-wrap">
            {directive.primary.text}
          </p>
          <p className="text-white/90 text-sm mt-1 whitespace-pre-wrap">
            <span className="font-semibold">Setup:</span> {directive.primary.setup}
          </p>
        </div>

        {/* Requirements & Risk in a compact row */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-black/30 rounded px-2 py-1 overflow-hidden">
            <span className="text-white/70">Need:</span>
            <span className="text-white ml-1 whitespace-pre-wrap">{directive.primary.requirements}</span>
          </div>
          <div className="bg-black/30 rounded px-2 py-1 overflow-hidden">
            <span className="text-white/70">Risk:</span>
            <span className="text-white ml-1 whitespace-pre-wrap">{directive.primary.risk}</span>
          </div>
        </div>

        {/* Backup Plans (collapsible look) */}
        {(directive.backupA || directive.backupB) && (
          <div className="text-xs space-y-1">
            {directive.backupA && (
              <div className="text-white/80 bg-black/20 rounded px-2 py-1 whitespace-pre-wrap">
                <span className="text-yellow-300">Plan B:</span> {directive.backupA}
              </div>
            )}
            {directive.backupB && (
              <div className="text-white/70 bg-black/20 rounded px-2 py-1 whitespace-pre-wrap">
                <span className="text-yellow-400">Plan C:</span> {directive.backupB}
              </div>
            )}
          </div>
        )}

        {/* Micro hints (role-specific) */}
        {Object.keys(directive.micro).length > 0 && (
          <div className="text-xs bg-purple-900/30 rounded px-2 py-1">
            <span className="text-purple-300 font-semibold">Team:</span>
            {Object.entries(directive.micro).map(([role, hint]) => (
              <span key={role} className="ml-2 text-white/80">
                {role}: {hint}
              </span>
            ))}
          </div>
        )}

        {/* Timers */}
        {Object.keys(directive.timers).length > 0 && (
          <div className="flex gap-2 flex-wrap text-xs">
            {Object.entries(directive.timers).map(([objective, seconds]) => (
              <span
                key={objective}
                className="bg-black/40 text-white px-2 py-0.5 rounded font-mono"
              >
                {objective}: {seconds}s
              </span>
            ))}
          </div>
        )}

        {/* Confidence indicator */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex-1 bg-black/30 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-green-400 h-full transition-all duration-500"
              style={{ width: `${directive.primary.confidence * 100}%` }}
            />
          </div>
          <span className="text-white/60 font-mono">
            {(directive.primary.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}
