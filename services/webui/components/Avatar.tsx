import { avatarColor, initials } from '@/lib/domain'

interface AvatarProps {
  id: number
  name: string
  size?: number
  radius?: number
  font?: number
}

/** Initials tile on a deterministic gradient keyed by id. */
export function Avatar({ id, name, size = 46, radius = 12, font = 16 }: AvatarProps) {
  const [c1, c2] = avatarColor(id)
  return (
    <div
      className="flex items-center justify-center font-bold text-white shrink-0"
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: radius,
        fontSize: font,
        background: `linear-gradient(135deg,${c1},${c2})`,
      }}
    >
      {initials(name)}
    </div>
  )
}
