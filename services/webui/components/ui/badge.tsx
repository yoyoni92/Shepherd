import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Pill badge. Pass explicit colors via style for the design's tinted status pills,
 * or use className for the neutral default.
 */
export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full text-[11px] font-bold px-2 py-0.5 whitespace-nowrap',
        className,
      )}
      {...props}
    />
  )
}
