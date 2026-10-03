import React, { useEffect, useState } from 'react'
import { users } from '../api'

const EMPTY = { login: '', password: '', full_name: '', role: 'user' }

export default function UsersAdmin() {
  const [list, setList] = useState([])
  const [form, setForm] = useState(EMPTY)

  const load = () => users.list().then((r) => setList(r.data)).catch(() => setList([]))
  useEffect(() => { load() }, [])

  const create = async () => {
    if (!form.login || !form.password) return
    await users.create(form)
    setForm(EMPTY)
    load()
  }
  const update = async (id, data) => { await users.update(id, data); load() }
  const remove = async (id) => {
    if (confirm('Удалить пользователя?')) { await users.remove(id); load() }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Управление пользователями</h2>

      <div className="bg-ink-900 border border-ink-800 rounded-lg p-4 mb-4 grid grid-cols-4 gap-3">
        <input
          value={form.login}
          onChange={(e) => setForm({ ...form, login: e.target.value })}
          placeholder="Логин"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm"
        />
        <input
          value={form.password}
          type="password"
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          placeholder="Пароль"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm"
        />
        <input
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          placeholder="ФИО"
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm"
        />
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
          className="bg-ink-850 border border-ink-700 rounded px-3 py-2 text-sm"
        >
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
        <div className="col-span-4 flex gap-2">
          <button onClick={create} className="bg-accent-500 text-white text-sm px-3 py-1.5 rounded">Добавить</button>
        </div>
      </div>

      <div className="overflow-x-auto bg-ink-900 border border-ink-800 rounded-lg">
        <table className="w-full text-sm">
          <thead className="text-slate-400 text-xs uppercase">
            <tr className="border-b border-ink-800">
              <th className="text-left p-3">ID</th>
              <th className="text-left p-3">Логин</th>
              <th className="text-left p-3">ФИО</th>
              <th className="text-left p-3">Роль</th>
              <th className="text-left p-3">Статус</th>
              <th className="text-right p-3">Действия</th>
            </tr>
          </thead>
          <tbody>
            {list.map((u) => (
              <tr key={u.id} className="border-b border-ink-800 hover:bg-ink-850/50">
                <td className="p-3 text-slate-400">{u.id}</td>
                <td className="p-3 font-medium text-white">{u.login}</td>
                <td className="p-3 text-slate-300">{u.full_name}</td>
                <td className="p-3">
                  <select
                    value={u.role}
                    onChange={(e) => update(u.id, { role: e.target.value })}
                    className="bg-ink-850 border border-ink-700 rounded px-2 py-1 text-xs"
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td className="p-3">
                  <button
                    onClick={() => update(u.id, { is_active: !u.is_active })}
                    className={`text-xs px-2 py-0.5 rounded ${u.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}
                  >
                    {u.is_active ? 'активен' : 'заблокирован'}
                  </button>
                </td>
                <td className="p-3 text-right space-x-2">
                  <button
                    onClick={() => { const p = prompt('Новый пароль:'); if (p) update(u.id, { password: p }) }}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    пароль
                  </button>
                  <button onClick={() => remove(u.id)} className="text-xs text-red-400 hover:text-red-300">Удалить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}