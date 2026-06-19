import * as React from 'react'
import { cn } from '@/lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'bg-bg border border-control rounded-[10px] px-3.5 py-3 text-sm text-ink outline-none focus:border-accent transition-colors',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'
