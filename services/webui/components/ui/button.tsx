import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-bold transition-[filter,background,border-color] disabled:opacity-50 disabled:pointer-events-none cursor-pointer outline-none',
  {
    variants: {
      variant: {
        primary:
          'text-white border-0 bg-[linear-gradient(135deg,#3b82f6,#1d4ed8)] shadow-[0_6px_16px_rgba(59,130,246,.28)] hover:brightness-110',
        secondary:
          'bg-panel2 border border-control text-muted hover:border-[#2b3550] hover:text-ink',
        danger:
          'bg-[#1a0f12] border border-[#3b1d22] text-danger hover:brightness-110',
        ghost: 'bg-transparent border-0 text-faint hover:text-ink',
        icon: 'bg-panel2 border border-control text-muted hover:text-ink hover:border-[#2b3550]',
      },
      size: {
        md: 'px-4 py-2.5 text-[13.5px]',
        sm: 'px-3 py-2 text-[12.5px]',
        lg: 'px-5 py-3 text-[15px]',
        icon: 'w-9 h-9 p-0',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  },
)
Button.displayName = 'Button'

export { buttonVariants }
