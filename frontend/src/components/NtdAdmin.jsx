import React, { useEffect, useState } from 'react'
import { ntd } from '../api'

const EMPTY = { number: '', title: '', doc_type: '', effective_date: '', status: 'actual', url: '', note: '' }

export default function NtdAdmin() {
  const [docs, setDocs] = useState([])
  const [expired, setExpired] = useState([])
  const [showNew, setShowNew] = useState(false)
  const [form, setForm] = useState(EMPTY)

  const load = () => {
    ntd.list().then((r) => setDocs(r.data))
    ntd.actualCheck().then((r) => setExpired(r.data.expired))
  }
  useEffect(() => { load() }, [])

  const create = async () => {
    await ntd.create(form)
    setShowNew(false)
    setForm(EMPTY)
    load()
  }
  const update = async (id, data) => { await ntd.update(id, data); load() }
  const remove = async (id) => {
    if (confirm('Удалить документ из базы?')) { await ntd.remove(id); load() }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">База нормативно-технических документов (НТД)</h2>
        <button
          onClick={() => setShowNew(!showNew)}
          className="bg-accent-500 hover:bg-accent-600 text-white text-sm px-3 py-1.5 rounded"
        >
          + Добавить
        </button>
      </div>

      {expired.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 text-sm">
          <div className="font-medium text-red-400 mb-1">
            Устаревшие/отменённые документы ({expired.length}):
          </div>
          <ul className="list-disc list-inside text-red-300">
            {expired.map((e, i) => <li key={i}><b>{e.number}</b> — {e.issue}</li>)}
          </ul>
        </div>
      )}

      {showNew && (
        <div className="bg-ink-900 border border-ink-800 rounded-lg p-4 mb-4 grid grid-cols-2 gap-3">
          <input
            value={form.number}
            onChange={(e) => setForm({ ...form, number: e.target.value })}
            placeholder="Номер (например, СП 6.13130.2021)"
            className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm"
          />
          <input
            value={form.doc_type}
            onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
            placeholder="Тип (ФЗ/СП/ГОСТ/ПУЭ)"
            className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm"
          />
          <input
            value={form.effective_date}
            onChange={(e) => setForm({ ...form, effective_date: e.target.value })}
            placeholder="Дата введения (гггг-мм-дд)"
            className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm col-span-2"
          />
          <textarea
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Наименование документа"
            className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm col-span-2 h-20 resize-none"
          />
          <input
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            placeholder="Ссылка (опц.)"
            className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm col-span-2"
          />
          <div className="col-span-2 flex gap-2">
            <button onClick={create} className="bg-accent-500 text-white text-sm px-3 py-1.5 rounded">Сохранить</button>
            <button onClick={() => setShowNew(false)} className="text-sm text-slate-400">Отмена</button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto bg-ink-900 border border-ink-800 rounded-lg">
        <table className="w-full text-sm">
          <thead className="text-slate-400 text-xs uppercase">
            <tr className="border-b border-ink-800">
              <th className="text-left p-3">Номер</th>
              <th className="text-left p-3">Наименование</th>
              <th className="text-left p-3">Тип</th>
              <th className="text-left p-3">Дата</th>
              <th className="text-left p-3">Статус</th>
              <th className="text-right p-3">Действия</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className="border-b border-ink-800 hover:bg-ink-850/50">
                <td className="p-3 font-medium text-white">{d.number}</td>
                <td className="p-3 text-slate-300">{d.title}</td>
                <td className="p-3 text-slate-400">{d.doc_type}</td>
                <td className="p-3 text-slate-400">{d.effective_date || '—'}</td>
                <td className="p-3"><StatusCell status={d.status} /></td>
                <td className="p-3 text-right">
                  <select
                    value={d.status}
                    onChange={(e) => update(d.id, { status: e.target.value })}
                    className="bg-ink-850 border border-ink-700 rounded px-2 py-1 text-xs mr-2"
                  >
                    <option value="actual">актуален</option>
                    <option value="expired">устарел</option>
                    <option value="superseded">отменён</option>
                  </select>
                  <button onClick={() => remove(d.id)} className="text-xs text-red-400 hover:text-red-300">Удалить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusCell({ status }) {
  const m = { actual: 'text-emerald-400', expired: 'text-red-400', superseded: 'text-amber-400' }
  const l = { actual: 'актуален', expired: 'устарел', superseded: 'отменён' }
  return <span className={`text-xs ${m[status]}`}>{l[status] || status}</span>
}