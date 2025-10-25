/**
 * ConnectionStatus - Small indicator for WebSocket connection status
 */

interface ConnectionStatusProps {
  isConnected: boolean;
}

export default function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  return (
    <div className="absolute top-2 right-2">
      <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}
        ${isConnected ? 'animate-pulse' : ''}`}
        title={isConnected ? 'Connected to backend' : 'Disconnected'}
      />
    </div>
  );
}
