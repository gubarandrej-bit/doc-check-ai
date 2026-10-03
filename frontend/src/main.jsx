import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { setTokenGetter } from './api'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <TokenBootstrap />
      <App />
    </BrowserRouter>
  </React.StrictMode>
)

function TokenBootstrap() {
  setTokenGetter(() => localStorage.getItem('dc_token'))
  return null
}