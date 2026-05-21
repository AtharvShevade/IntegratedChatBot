import { useState, useEffect } from 'react'
import Home from './pages/Home/Home'

export default function App() {
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem('theme') === 'dark'
  )

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [darkMode])

  const toggleDark = () => setDarkMode((d) => !d)

  return <Home darkMode={darkMode} toggleDark={toggleDark} />
}
