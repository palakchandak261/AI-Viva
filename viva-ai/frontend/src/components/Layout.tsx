import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import {
  LayoutDashboard, Upload, BarChart2, Users, LogOut,
  BrainCircuit, ChevronRight, Sparkles, GraduationCap
} from 'lucide-react'
import clsx from 'clsx'

const studentNav = [
  { to: '/dashboard', label: 'Dashboard',      icon: LayoutDashboard },
  { to: '/upload',    label: 'Upload Project',  icon: Upload },
  { to: '/analytics', label: 'My Analytics',   icon: BarChart2 },
]

const facultyNav = [
  { to: '/faculty', label: 'Faculty Panel', icon: Users },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  const isFaculty = user?.role === 'faculty' || user?.role === 'admin'
  const navItems = isFaculty ? facultyNav : studentNav

  return (
    <div className="flex h-screen bg-dark-950 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col border-r border-white/5 bg-dark-900/80 backdrop-blur-xl">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-6 border-b border-white/5">
          <div className="relative">
            <div className="w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-glow-sm">
              <BrainCircuit size={18} className="text-white" />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-400 rounded-full border-2 border-dark-900" />
          </div>
          <div>
            <span className="font-bold text-white text-sm tracking-tight">AI Viva</span>
            <p className="text-xs text-slate-500">{isFaculty ? 'Faculty Portal' : 'Student Portal'}</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => clsx(
                'group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-brand-gradient text-white shadow-glow-sm'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              )}
            >
              {({ isActive }) => (
                <>
                  <Icon size={17} className={isActive ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'} />
                  {label}
                  {isActive && <ChevronRight size={13} className="ml-auto opacity-70" />}
                </>
              )}
            </NavLink>
          ))}

          {/* Role badge */}
          <div className="mt-4 mx-1 p-3 rounded-xl bg-brand-950/50 border border-brand-800/30">
            <div className="flex items-center gap-2 mb-1">
              {isFaculty
                ? <GraduationCap size={13} className="text-brand-400" />
                : <Sparkles size={13} className="text-brand-400" />}
              <span className="text-xs font-semibold text-brand-300 capitalize">{user?.role} Account</span>
            </div>
            <p className="text-xs text-slate-500">
              {isFaculty
                ? 'Monitor student performance and integrity'
                : 'Upload your project and take an AI viva exam'}
            </p>
          </div>
        </nav>

        {/* User footer */}
        <div className="px-3 py-4 border-t border-white/5">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white/5 mb-1">
            <div className="w-8 h-8 rounded-lg bg-brand-gradient flex items-center justify-center text-white font-bold text-sm shadow-glow-sm">
              {user?.name?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-200 truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
            </div>
          </div>
          <button onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-xs text-slate-500 hover:text-red-400 hover:bg-red-400/5 rounded-lg transition-all duration-200">
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-dark-950">
        <div className="fixed top-0 left-64 right-0 h-px bg-gradient-to-r from-brand-600/50 via-purple-600/30 to-transparent z-10" />
        <div className="max-w-5xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
