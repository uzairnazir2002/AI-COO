"use client";

import { useId } from "react";

export function ChartFrame({
  label,
  description,
  className,
  children,
}: {
  label: string;
  description: string;
  className: string;
  children: React.ReactNode;
}) {
  const descriptionId = useId();
  return (
    <figure role="img" aria-label={label} aria-describedby={descriptionId} className={className}>
      <figcaption id={descriptionId} className="sr-only">
        {description}
      </figcaption>
      {children}
    </figure>
  );
}

