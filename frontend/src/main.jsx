import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
// Theme CSS is loaded dynamically from App.jsx based on APP_VERSION (5.5 vs 6.0) —
// see the _isV6 check and dynamic import() near the top of App.jsx.

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
