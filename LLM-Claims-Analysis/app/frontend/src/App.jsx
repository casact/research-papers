import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import axios from 'axios'
import Layout from './components/Layout'
import Home from './pages/Home'
import ProcessBundle from './pages/ProcessBundle'
import AddDocs from './pages/AddDocs'
import ProcessText from './pages/ProcessText'
import Documents from './pages/Documents'

// Component to handle scroll to top on route change
function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: 'smooth'
    })
  }, [pathname])

  return null
}

function App() {
  const [apiInfo, setApiInfo] = useState(null)
  const [apiStatus, setApiStatus] = useState('connecting')

  useEffect(() => {
    const fetchApiInfo = async () => {
      try {
        const [healthRes, infoRes] = await Promise.all([
          axios.get('/api/health'),
          axios.get('/api/info')
        ])
        setApiStatus(healthRes.data.status)
        setApiInfo(infoRes.data)
      } catch (error) {
        console.error('API connection failed:', error)
        setApiStatus('error')
      }
    }
    fetchApiInfo()
  }, [])

  return (
    <BrowserRouter>
      <ScrollToTop />
      <Layout apiStatus={apiStatus}>
        <Routes>
          <Route path="/" element={<Home apiInfo={apiInfo} />} />
          <Route path="/process-bundle" element={<ProcessBundle />} />
          <Route path="/add-docs" element={<AddDocs />} />
          <Route path="/process-text" element={<ProcessText />} />
          <Route path="/documents" element={<Documents />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
