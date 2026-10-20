"use client";
import type { ReactNode } from "react";
export function Reveal({ children, className = "", delay = "" }: { children: ReactNode; className?: string; delay?: string }) { return <div className={`reveal ${delay} ${className}`}>{children}</div>; }
