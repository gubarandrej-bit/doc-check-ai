import React, { useEffect, useState } from 'react'
import { aiModels } from '../api'

export default function ModelsAdmin() {
  const [list, setList] = useState([])
  const [plugins, setPlugins] = useState([])
  const [form, setForm] = useState({ name: '', provider: 'openrouter', model_id: '', mode: 'cloud', capabilities: 'text', api_key: '', base_url: '', description: '', is_default: false })
  const EMPTY = { name: '', provider: 'openrouter', model_id: '', mode: 'cloud', capabilities: 'text', api_key: '', base_url: '', description: '', is_default: false }

  const load = () => aiModels.list().then((r) => setList(r.data)).catch(() => setList([]))
  useEffect(() => {
    load()
    aiModels.plugins().then((r) => setPlugins(r.data)).catch(() => setPlugins([]))
  }, [])

  const create = async () => {
    if (!form.name || !form.model_id) return
    await aiModels.create(form)
    setForm(EMPTY)
    load()
  }
  const update = async (id, data) => { await aiModels.update(id, data); load() }
  const remove = async (id) => { if (confirm('Удалить модель?')) { await aiModels.remove(id); load() } }

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Управление моделями ИИ</h2>
      <p className="text-sm text-slate-400 mb-4">
        Добавляйте/удаляйте модели. Облачные — через API (OpenRouter и др.), локальные — через Ollama.
        При отсутствии данных проверки не проводятся и сообщается причина.
      </p>

      {plugins.length > 0 && (
        <div className="bg-ink-900 border border-ink-800 rounded-lg p-4 mb-4">
          <div className="text-sm text-white mb-2">Плагины анализа</div>
          <div className="space-y-1">
            {plugins.map((p) => (
              <div key={p.code} className="text-xs text-slate-400 flex gap-2 flex-wrap">
                <span className="font-mono text-accent-400">{p.code}</span>
                <span className="text-slate-300">{p.name}</span>
                <span className={p.needs_model ? 'text-amber-400/80' : 'text-emerald-400/80'}>
                  {p.needs_model ? `нужна модель: ${p.capability}` : 'модель не требуется'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-ink-900 border border-ink-800 rounded-lg p-4 mb-4 grid grid-cols-3 gap-3">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Название"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm" />
        <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm">
          <option value="openrouter">openrouter</option><option value="ollama">ollama (локально)</option><option value="custom">custom</option>
        </select>
        <input value={form.model_id} onChange={(e) => setForm({ ...form, model_id: e.target.value })} placeholder="model_id (например, openrouter/free)"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm" />
        <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm">
          <option value="cloud">cloud</option><option value="local">local</option>
        </select>
        <label className="flex items-center gap-2 bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm text-slate-300">
          <input type="checkbox" checked={form.capabilities.includes('vision')}
            onChange={(e) => setForm({ ...form,
              capabilities: e.target.checked ? 'text vision' : 'text' })} />
          мультимодальная (vision)
        </label>
        <input value={form.api_key} type="password" onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="API ключ (опц.)"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm" />
        <input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="Базовый URL (опц.)"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm" />
        <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Описание"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm col-span-3 h-16 resize-none" />
        <div className="col-span-3 flex items-center gap-2">
          <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
          <span className="text-xs text-slate-400">сделать модель по умолчанию</span>
          <button onClick={create} className="ml-auto bg-accent-500 text-white text-sm px-3 py-1.5 rounded">Добавить</button>
        </div>
      </div>

      <div className="overflow-x-auto bg-ink-900 border border-ink-800 rounded-lg">
        <table className="w-full text-sm">
          <thead className="text-slate-400 text-xs uppercase">
            <tr className="border-b border-ink-800">
              <th className="text-left p-3">Название</th><th className="text-left p-3">Провайдер</th>
              <th className="text-left p-3">model_id</th><th className="text-left p-3">Режим</th>
              <th className="text-left p-3">Способности</th>
              <th className="text-left p-3">По умолч.</th><th className="text-left p-3">Активна</th><th className="text-right p-3">Действия</th>
            </tr>
          </thead>
          <tbody>
            {list.map((m) => (
              <tr key={m.id} className="border-b border-ink-800 hover:bg-ink-850/50">
                <td className="p-3 font-medium text-white">{m.name}</td>
                <td className="p-3 text-slate-300">{m.provider}</td>
                <td className="p-3 text-slate-400 font-mono text-xs">{m.model_id}</td>
                <td className="p-3 text-slate-300">{m.mode}</td>
                <td className="p-3">
                  <label className="flex items-center gap-1.5 text-xs text-slate-300 whitespace-nowrap">
                    <input type="checkbox" checked={(m.capabilities || '').includes('vision')}
                      onChange={(e) => update(m.id, { capabilities: e.target.checked ? 'text vision' : 'text' })} />
                    vision
                  </label>
                </td>
                <td className="p-3">
                  <input type="checkbox" checked={m.is_default} onChange={(e) => update(m.id, { is_default: e.target.checked })} />
                </td>
                <td className="p-3">
                  <button onClick={() => update(m.id, { is_active: !m.is_active })}
                    className={`text-xs px-2 py-0.5 rounded ${m.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                    {m.is_active ? 'да' : 'нет'}
                  </button>
                </td>
                <td className="p-3 text-right">
                  <button onClick={() => remove(m.id)} className="text-xs text-red-400 hover:text-red-300">Удалить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}