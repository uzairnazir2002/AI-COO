"use client";

import { useEffect, useRef, useState } from "react";

export function ChartCanvas({
  className,
  children,
}: {
  className: string;
  children: (size: { width: number; height: number }) => React.ReactNode;
}) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = hostRef.current;
    if (!element) return;

    const update = () => {
      const rect = element.getBoundingClientRect();
      setSize({
        width: Math.max(0, Math.floor(rect.width)),
        height: Math.max(0, Math.floor(rect.height)),
      });
    };

    update();
    const observer = new ResizeObserver(() => update());
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={hostRef} className={className}>
      {size.width > 16 && size.height > 16 ? children(size) : null}
    </div>
  );
}

