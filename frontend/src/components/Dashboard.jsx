import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { checks, ntd, projects } from '../api'

export default function Dashboard() {
  const [stats, setStats] = useState({ projects: 0, ntd: 0, expired: 0, runs: 0 })

  const load = async () => {
    try {
      const [p, n] = await Promise.all([projects.list(), ntd.list()])
      const expired = n.data.filter((d) => d.status !== 'actual').length
      let runs = 0
      for (const pr of p.data) {
        const rr = await checks.listRuns(pr.id)
        runs += rr.data.length
      }
      setStats({ projects: p.data.length, ntd: n.data.length, expired, runs })
    } catch (e) {
      console.error(e)
    }
  }
  useEffect(() => { load() }, [])

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Дашборд</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Card label="Проектов" value={stats.projects} />
        <Card label="НТД в базе" value={stats.ntd} />
        <Card label="Устаревших НТД" value={stats.expired} tone="red" />
        <Card label="Запусков проверок" value={stats.runs} />
      </div>
      <div className="bg-ink-900 border border-ink-800 rounded-lg p-4">
        <div className="font-medium text-white mb-2">Быстрые действия</div>
        <div className="flex gap-3 flex-wrap">
          <Link to="/projects" className="text-sm bg-accent-500 hover:bg-accent-600 text-white px-3 py-2 rounded-md">
            Открыть проекты
          </Link>
          <Link to="/reports" className="text-sm bg-ink-800 hover:bg-ink-700 text-slate-200 px-3 py-2 rounded-md">
            Отчёты
          </Link>
        </div>
      </div>
    </div>
  )
}

function Card({ label, value, tone = 'white' }) {
  const c = { white: 'text-white', red: 'text-red-400' }[tone]
  return (
    <div className="bg-ink-900 border border-ink-800 rounded-lg p-4">
      <div className={`text-2xl font-semibold ${c}`}>{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  )
}