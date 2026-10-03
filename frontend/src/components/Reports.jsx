import React, { useEffect, useState } from 'react'
import { checks, projects, reports } from '../api'

export default function Reports() {
  const [projList, setProjList] = useState([])
  const [runs, setRuns] = useState([])
  const [pid, setPid] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    projects.list().then((r) => setProjList(r.data)).catch(() => setProjList([]))
  }, [])

  const loadRuns = (id) => {
    setPid(id)
    if (id) checks.listRuns(id).then((r) => setRuns(r.data)).catch(() => setRuns([]))
    else setRuns([])
  }

  const gen = async (runId, fmt) => {
    setBusy(true)
    try { await reports.generate({ run_id: runId, format: fmt }) }
    finally { setBusy(false) }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Отчёты и результаты проверок</h2>
      <div className="mb-4">
        <label className="text-sm text-slate-400">Проект: </label>
        <select
          value={pid}
          onChange={(e) => loadRuns(e.target.value)}
          className="bg-ink-850 border border-ink-700 rounded px-3 py-1.5 text-sm"
        >
          <option value="">— выберите —</option>
          {projList.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {runs.length === 0 ? (
        <div className="text-slate-500 text-sm">
          Для проекта нет запусков проверок. Запустите проверку на странице проекта.
        </div>
      ) : (
        <div className="overflow-x-auto bg-ink-900 border border-ink-800 rounded-lg">
          <table className="w-full text-sm">
            <thead className="text-slate-400 text-xs uppercase">
              <tr className="border-b border-ink-800">
                <th className="text-left p-3">Запуск</th>
                <th className="text-left p-3">Режим</th>
                <th className="text-left p-3">Статус</th>
                <th className="text-left p-3">Дата</th>
                <th className="text-left p-3">Проверок</th>
                <th className="text-right p-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id} className="border-b border-ink-800 hover:bg-ink-850/50">
                  <td className="p-3 font-medium text-white">#{r.run_id}</td>
                  <td className="p-3 text-slate-300">{r.mode}</td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${r.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-400">{r.created_at}</td>
                  <td className="p-3 text-slate-300">{r.items_count}</td>
                  <td className="p-3 text-right space-x-2">
                    <button
                      disabled={busy}
                      onClick={() => gen(r.run_id, 'docx')}
                      className="text-xs bg-ink-800 hover:bg-ink-700 text-slate-200 px-2 py-1 rounded"
                    >
                      DOC
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => gen(r.run_id, 'xlsx')}
                      className="text-xs bg-ink-800 hover:bg-ink-700 text-slate-200 px-2 py-1 rounded"
                    >
                      XLS
                    </button>
                    <button
                      onClick={async () => {
                        if (confirm('Удалить результаты проверки?')) {
                          await reports.deleteRun(r.run_id)
                          loadRuns(pid)
                        }
                      }}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}