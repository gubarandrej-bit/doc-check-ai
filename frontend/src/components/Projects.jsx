import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { checks, projects } from '../api'

export default function Projects() {
  const [list, setList] = useState([])
  const [showNew, setShowNew] = useState(false)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  const load = () => projects.list().then((r) => setList(r.data)).catch(() => setList([]))
  useEffect(() => { load() }, [])

  const create = async () => {
    if (!name.trim()) return
    setBusy(true)
    try {
      const r = await projects.create({ name: name.trim() })
      setName('')
      setShowNew(false)
      await load()
      navigate(`/project/${r.data.id}`)
    } finally { setBusy(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Проекты</h2>
        <button
          onClick={() => setShowNew(!showNew)}
          className="bg-accent-500 hover:bg-accent-600 text-white text-sm px-3 py-1.5 rounded-md"
        >
          + Новый проект
        </button>
      </div>

      {showNew && (
        <div className="bg-ink-900 border border-ink-800 rounded-lg p-4 mb-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Название проекта"
            className="w-full bg-ink-850 border border-ink-700 rounded-md px-3 py-2 text-sm mb-3 focus:outline-none focus:border-accent-500"
          />
          <div className="flex gap-2">
            <button
              disabled={busy}
              onClick={create}
              className="bg-accent-500 text-white text-sm px-3 py-1.5 rounded-md"
            >
              Создать
            </button>
            <button onClick={() => setShowNew(false)} className="text-sm text-slate-400">Отмена</button>
          </div>
        </div>
      )}

      {list.length === 0 ? (
        <div className="text-slate-500 text-sm">Проектов пока нет. Создайте первый.</div>
      ) : (
        <div className="grid gap-3">
          {list.map((p) => <ProjectCard key={p.id} p={p} onRefresh={load} />)}
        </div>
      )}
    </div>
  )
}

function ProjectCard({ p, onRefresh }) {
  const [uploading, setUploading] = useState(false)
  const [running, setRunning] = useState(false)
  const [mode, setMode] = useState('local')
  const [modelId, setModelId] = useState('')
  const fileRef = React.useRef(null)
  const navigate = useNavigate()

  const onUpload = async (e) => {
    const files = e.target.files
    if (!files.length) return
    setUploading(true)
    try {
      await projects.upload(p.id, Array.from(files))
      await onRefresh()
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const run = async () => {
    setRunning(true)
    try {
      const r = await checks.run({ project_id: p.id, mode, model_id: modelId ? Number(modelId) : null })
      navigate(`/check/${r.data.run_id}`)
    } finally { setRunning(false) }
  }

  return (
    <div className="bg-ink-900 border border-ink-800 rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-medium text-white">{p.name}</div>
          {p.description && <div className="text-sm text-slate-400">{p.description}</div>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/project/${p.id}`)}
            className="text-xs bg-ink-800 hover:bg-ink-700 text-slate-200 px-2 py-1 rounded"
          >
            Открыть
          </button>
          <button
            disabled={running}
            onClick={run}
            className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded disabled:opacity-50"
          >
            {running ? 'Проверяю…' : 'Проверить'}
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="bg-ink-850 border border-ink-700 rounded px-2 py-1 text-slate-200"
        >
          <option value="local">Локальный</option>
          <option value="cloud">Облачный</option>
          <option value="hybrid">Гибридный</option>
        </select>
        <input
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          placeholder="ID модели ИИ (опц.)"
          className="bg-ink-850 border border-ink-700 rounded px-2 py-1 text-slate-200 w-28"
        />
        <label className="text-slate-400">
          Файлы:
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".xls,.xlsx,.doc,.docx,.pdf,.dwg,.zip"
            onChange={onUpload}
            className="ml-1 text-xs"
          />
        </label>
        {uploading && <span className="text-slate-400">загрузка…</span>}
      </div>

      {p.files && p.files.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {p.files.map((f) => (
            <span
              key={f.id}
              className="text-xs bg-ink-850 border border-ink-700 rounded px-2 py-0.5 text-slate-300"
            >
              {f.filename} <span className="text-slate-500">({f.file_type})</span>
            </span>
          ))}
        </div>
      ) : (
        <div className="mt-3 text-xs text-amber-400/80">
          Файлы не загружены — проверка не будет иметь данных.
        </div>
      )}
    </div>
  )
}