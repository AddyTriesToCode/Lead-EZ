import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import './styles/App.css'
import Dashboard from './pages/Dashboard'
import History from './pages/History'

function Navigation() {
  const location = useLocation()
  
  return (
    <nav className="app-nav">
      <Link 
        to="/" 
        className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
      >
        📊 Dashboard
      </Link>
      <Link 
        to="/history" 
        className={`nav-link ${location.pathname === '/history' ? 'active' : ''}`}
      >
        📜 History
      </Link>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>Lead-EZ Dashboard</h1>
          <p>AI-Powered Lead Generation & Messaging Pipeline</p>
          <Navigation />
        </header>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </Router>
  )

}

export default App
