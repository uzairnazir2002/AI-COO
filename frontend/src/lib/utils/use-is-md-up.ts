"use client";

import { useLayoutEffect, useState } from "react";

/** Matches Tailwind default `md` screen. */
export const MD_BREAKPOINT_PX = 768;

/** True when viewport is at least Tailwind's `md` breakpoint. */
export function useIsMdUp() {
  const [isMdUp, setIsMdUp] = useState(false);

  useLayoutEffect(() => {
    const sync = () => setIsMdUp(window.innerWidth >= MD_BREAKPOINT_PX);
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, []);

  return isMdUp;
}
