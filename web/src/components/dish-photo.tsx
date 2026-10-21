"use client";

import Image from "next/image";
import { useState } from "react";

import { cn } from "@/lib/utils";

/** The dish's illustration, or nothing if it has none yet. Photos are small WebP files. */
export function DishPhoto({
  id,
  name,
  size,
  className,
  priority = false,
}: {
  id: string;
  name: string;
  size: number;
  className?: string;
  priority?: boolean;
}) {
  const [missing, setMissing] = useState(false);
  if (missing) return null;
  return (
    <Image
      src={`/dishes/${id}.webp`}
      alt={name}
      width={size}
      height={size}
      unoptimized
      priority={priority}
      onError={() => setMissing(true)}
      className={cn("bg-muted object-cover", className)}
    />
  );
}
