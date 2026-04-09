import { Link, NavLink } from 'react-router-dom'
import { useMe } from '../../hooks/useAuth.ts'
import AppSwitcher from './AppSwitcher.tsx'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: '◫' },
  { to: '/locations', label: 'Locations', icon: '◰' },
  { to: '/items', label: 'Items', icon: '⊡' },
  { to: '/add', label: 'Add Item', icon: '+' },
  { to: '/media', label: 'Media', icon: '♫' },
  { to: '/search', label: 'Search', icon: '⌕' },
  { to: '/amazon', label: 'Amazon', icon: '⏣' },
  { to: '/ebay', label: 'eBay', icon: '⊞' },
]

interface SidebarProps {
  className?: string
  onNavigate?: () => void
}

export default function Sidebar({ className, onNavigate }: SidebarProps) {
  const { data: user } = useMe()

  return (
    <aside className={`w-52 bg-bg-secondary border-r border-border flex flex-col shrink-0 ${className ?? ''}`}>
      <div className="p-4 border-b border-border flex items-center justify-between">
        <Link to="/" className="text-lg font-bold text-accent hover:text-accent-hover transition-colors">Stuff</Link>
        <AppSwitcher currentApp="Stuff" />
      </div>
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-accent/15 text-accent font-medium'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      {user && (
        <div className="p-3 border-t border-border">
          <div className="text-sm text-text-primary truncate">{user.display_name}</div>
          <div className="text-xs text-text-secondary truncate">{user.email}</div>
        </div>
      )}
    </aside>
  )
}
