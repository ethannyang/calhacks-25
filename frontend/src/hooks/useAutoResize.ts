/**
 * Hook to automatically resize the Electron window based on content size
 */
import { useEffect, useRef } from 'react';

export function useAutoResize(enabled: boolean = true) {
  const contentRef = useRef<HTMLDivElement>(null);
  const lastSizeRef = useRef({ width: 0, height: 0 });

  useEffect(() => {
    if (!window.electron) return;

    // Enable/disable auto-resize
    window.electron.setAutoResize(enabled);
  }, [enabled]);

  useEffect(() => {
    if (!window.electron || !enabled) return;

    const measureAndResize = () => {
      if (!contentRef.current) return;

      // Get the actual content size
      const rect = contentRef.current.getBoundingClientRect();
      const scrollHeight = contentRef.current.scrollHeight;
      const scrollWidth = contentRef.current.scrollWidth;

      // Use the larger of visual size or scroll size
      const width = Math.max(rect.width, scrollWidth);
      const height = Math.max(rect.height, scrollHeight);

      // Add some padding for the window chrome
      const windowWidth = Math.ceil(width + 40);  // 20px padding on each side
      const windowHeight = Math.ceil(height + 40); // 20px padding top/bottom

      // Only resize if size changed significantly (>10px difference)
      const lastSize = lastSizeRef.current;
      if (Math.abs(windowWidth - lastSize.width) > 10 ||
          Math.abs(windowHeight - lastSize.height) > 10) {

        window.electron?.setPreferredSize(windowWidth, windowHeight);
        lastSizeRef.current = { width: windowWidth, height: windowHeight };
      }
    };

    // Measure immediately
    measureAndResize();

    // Set up ResizeObserver to watch for content changes
    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(measureAndResize);
    });

    if (contentRef.current) {
      resizeObserver.observe(contentRef.current);
    }

    // Also measure when content might change
    const timeoutId = setTimeout(measureAndResize, 100);

    return () => {
      resizeObserver.disconnect();
      clearTimeout(timeoutId);
    };
  }, [enabled]);

  return contentRef;
}