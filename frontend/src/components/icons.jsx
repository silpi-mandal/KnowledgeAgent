const baseProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
}

export function MenuIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  )
}

export function CloseIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  )
}

export function PlusIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function FileIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
    </svg>
  )
}

export function ChevronIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

export function SendIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  )
}

export function AlertIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  )
}

export function SunIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  )
}

export function MoonIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

export function ThumbUpIcon({ className, filled = false }) {
  return (
    <svg className={className} {...baseProps} fill={filled ? 'currentColor' : 'none'}>
      <path d="M7 10v11H3V10zM7 10l4-8a2.5 2.5 0 0 1 2.5 2.5V9H19a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 17.6 21H7" />
    </svg>
  )
}

export function ThumbDownIcon({ className, filled = false }) {
  return (
    <svg className={className} {...baseProps} fill={filled ? 'currentColor' : 'none'}>
      <path d="M17 14V3h4v11zM17 14l-4 8a2.5 2.5 0 0 1-2.5-2.5V15H5a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 6.4 3H17" />
    </svg>
  )
}

export function WrenchIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z" />
    </svg>
  )
}

export function LogoutIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
    </svg>
  )
}

export function LayersIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="m12 2 10 5-10 5L2 7zM2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  )
}

export function ShieldIcon({ className }) {
  return (
    <svg className={className} {...baseProps}>
      <path d="M12 3l8 3v6c0 4.5-3.2 8.3-8 9-4.8-.7-8-4.5-8-9V6z" />
    </svg>
  )
}
