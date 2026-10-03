import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { checks, reports } from '../api'

const STATUS_STYLE = {
  passed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  failed: 'bg-red-500/15 text-red-400 border-red-500/30',
  not_performed: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
}
const STATUS_LABEL = { passed: 'ПРОЙДЕНА', failed: 'НАРУШЕНИЕ', not_performed: 'НЕ ПРОВЕДЕНА' }

export default function CheckRun() {
  const { runId } = useParams()
  const navigate = useNavigate()
  const [run, setRun] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = () => checks.getRun(runId).then((r) => setRun(r.data)).catch(() => setRun(null))
  useEffect(() => { load() }, [runId])

  if (!run) return <div className="text-slate-500 text-sm">Загрузка…</div>

  const items = run.items || []
  const passed = items.filter((i) => i.status === 'passed').length
  const failed = items.filter((i) => i.status === 'failed').length
  const skipped = items.filter((i) => i.status === 'not_performed').length

  const gen = async (fmt) => {
    setBusy(true)
    try { await reports.generate({ run_id: Number(runId), format: fmt }) }
    finally { setBusy(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold text-white">Результаты проверки #{run.run_id}</h2>
          <div className="text-sm text-slate-400">
            Проект ID: {run.project_id} · Режим: {run.mode} · {run.created_at}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            disabled={busy}
            onClick={() => gen('docx')}
            className="text-xs bg-ink-800 hover:bg-ink-700 text-slate-200 px-3 py-1.5 rounded"
          >
            Скачать DOC
          </button>
          <button
            disabled={busy}
            onClick={() => gen('xlsx')}
            className="text-xs bg-ink-800 hover:bg-ink-700 text-slate-200 px-3 py-1.5 rounded"
          >
            Скачать XLS
          </button>
          <button
            onClick={() => navigate(-1)}
            className="text-xs bg-ink-800 hover:bg-ink-700 text-slate-200 px-3 py-1.5 rounded"
          >
            Назад
          </button>
        </div>
      </div>

      {run.summary && (
        <div className="bg-ink-900 border border-ink-800 rounded-lg p-3 text-sm text-slate-300 mb-4">
          {run.summary}
        </div>
      )}

      <div className="grid grid-cols-3 gap-3 mb-5">
        <Stat label="Проведено" value={passed} tone="emerald" />
        <Stat label="Нарушения" value={failed} tone="red" />
        <Stat label="Не проведено" value={skipped} tone="amber" />
      </div>

      <div className="space-y-3">
        {items.map((i) => (
          <div key={i.id} className="bg-ink-900 border border-ink-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className={`text-xs px-2 py-0.5 rounded border mt-0.5 ${STATUS_STYLE[i.status]}`}>
                {STATUS_LABEL[i.status]}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-white text-sm">{i.name}</div>
                <div className="text-xs text-slate-500">Код: {i.code} · Категория: {i.category}</div>
                {i.detail && <div className="text-sm text-slate-300 mt-1">{i.detail}</div>}
                {i.status === 'not_performed' && i.reason_skipped && (
                  <div className="mt-2 bg-amber-500/10 border border-amber-500/30 rounded p-2 text-sm text-amber-300">
                    <span className="font-medium">Причина: </span>{i.reason_skipped}
                  </div>
                )}
                {i.ntd_refs && <div className="text-xs text-slate-400 mt-1">НТД: {i.ntd_refs}</div>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Stat({ label, value, tone }) {
  const map = { emerald: 'text-emerald-400', red: 'text-red-400', amber: 'text-amber-400' }
  return (
    <div className="bg-ink-900 border border-ink-800 rounded-lg p-3">
      <div className={`text-2xl font-semibold ${map[tone]}`}>{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  )
}