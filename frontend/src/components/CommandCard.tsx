/**
 * CommandCard - Displays coaching command with priority-based styling
 */

import { CoachingCommand } from '../store/coachingStore';

interface CommandCardProps {
  command: CoachingCommand;
}

const priorityStyles = {
  critical: 'bg-red-600/95 border-red-400 shadow-red-500/50',
  high: 'bg-orange-600/90 border-orange-400 shadow-orange-500/40',
  medium: 'bg-blue-600/85 border-blue-400 shadow-blue-500/30',
  low: 'bg-gray-600/80 border-gray-400 shadow-gray-500/20',
};

const priorityText = {
  critical: 'animate-pulse',
  high: '',
  medium: '',
  low: '',
};

export default function CommandCard({ command }: CommandCardProps) {
  const styleClass = priorityStyles[command.priority];
  const textClass = priorityText[command.priority];

  return (
    <div
      className={`${styleClass} ${textClass}
        rounded-lg border-2 shadow-2xl
        px-4 py-3 min-w-[350px] max-w-[450px]
        transition-all duration-300 ease-in-out`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <span className="text-3xl flex-shrink-0 mt-0.5">{command.icon}</span>

        {/* Message */}
        <div className="flex-1">
          <p className="text-white font-bold text-base leading-tight tracking-wide">
            {command.message}
          </p>

          {/* Category badge */}
          <span className="inline-block mt-2 text-xs uppercase tracking-wider
            bg-black/30 text-white/80 px-2 py-0.5 rounded">
            {command.category}
          </span>
        </div>
      </div>
    </div>
  );
}
