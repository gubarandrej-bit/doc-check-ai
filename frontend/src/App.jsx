import React, { useEffect, useState } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { auth } from './api'
import CheckRun from './components/CheckRun'
import Dashboard from './components/Dashboard'
import ModelsAdmin from './components/ModelsAdmin'
import NtdAdmin from './components/NtdAdmin'
import Projects from './components/Projects'
import Reports from './components/Reports'
import UsersAdmin from './components/UsersAdmin'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const loc = useLocation()

  useEffect(() => {
    const t = localStorage.getItem('dc_token')
    if (!t) { setLoading(false); return }
    auth.me()
      .then((r) => { setUser(r.data) })
      .catch(() => { localStorage.removeItem('dc_token'); setUser(null) })
      .finally(() => setLoading(false))
  }, [loc])

  const login = async (login, password) => {
    const r = await auth.login({ login, password })
    localStorage.setItem('dc_token', r.data.access_token)
    setUser(r.data.user)
  }
  const logout = () => { localStorage.removeItem('dc_token'); setUser(null) }

  if (loading) {
    return (
      <div className="min-h-screen bg-ink-950 flex items-center justify-center text-slate-400">
        Загрузка…
      </div>
    )
  }
  if (!user) return <Login onLogin={login} />

  return (
    <div className="min-h-screen bg-ink-950">
      <nav className="bg-ink-900/80 border-b border-ink-800 sticky top-0 z-20 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 flex items-center gap-4 h-14">
          <Link to="/" className="flex items-center gap-2 font-semibold text-white">
            <span className="inline-block w-3 h-3 rounded-full bg-accent-500" /> DocCheck
          </Link>
          <div className="flex-1 flex gap-1 text-sm text-slate-300 overflow-x-auto">
            <Nav to="/projects" label="Проекты" />
            <Nav to="/reports" label="Отчёты" />
            {user.role === 'admin' && <Nav to="/ntd" label="НТД" />}
            {user.role === 'admin' && <Nav to="/users" label="Пользователи" />}
            {user.role === 'admin' && <Nav to="/models" label="Модели ИИ" />}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-400">{user.full_name || user.login}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${user.role === 'admin' ? 'bg-accent-500/20 text-accent-400' : 'bg-ink-700 text-slate-300'}`}>
              {user.role}
            </span>
            <button onClick={logout} className="text-slate-400 hover:text-white">Выйти</button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/ntd" element={<NtdAdmin />} />
          <Route path="/users" element={<UsersAdmin />} />
          <Route path="/models" element={<ModelsAdmin />} />
          <Route path="/project/:id" element={<Projects />} />
          <Route path="/check/:runId" element={<CheckRun />} />
        </Routes>
      </main>
    </div>
  )
}

function Nav({ to, label }) {
  const loc = useLocation()
  const active = loc.pathname === to || loc.pathname.startsWith(to + '/')
  return (
    <Link
      to={to}
      className={`px-3 py-1.5 rounded-md ${active ? 'bg-accent-500/15 text-accent-400' : 'hover:bg-ink-800 text-slate-300'}`}
    >
      {label}
    </Link>
  )
}

function Login({ onLogin }) {
  const [login, setLogin] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try { await onLogin(login, pw) }
    catch (e) { setErr(e.response?.data?.detail || 'ошибка входа') }
    finally { setBusy(false) }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-ink-950">
      <div className="w-full max-w-sm bg-ink-900 border border-ink-800 rounded-xl p-6">
        <h1 className="text-xl font-semibold text-white mb-1">DocCheck</h1>
        <p className="text-sm text-slate-400 mb-5">Проверка технической документации</p>
        <form onSubmit={submit} className="space-y-3">
          <input
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            placeholder="Логин"
            className="w-full bg-ink-850 border border-ink-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent-500"
          />
          <input
            type="password"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            placeholder="Пароль"
            className="w-full bg-ink-850 border border-ink-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent-500"
          />
          {err && <div className="text-sm text-red-400">{err}</div>}
          <button
            disabled={busy}
            className="w-full bg-accent-500 hover:bg-accent-600 disabled:opacity-50 text-white rounded-md py-2 text-sm font-medium"
          >
            Войти
          </button>
        </form>
        <p className="text-xs text-slate-500 mt-4">По умолчанию: admin / admin123</p>
      </div>
    </div>
  )
}