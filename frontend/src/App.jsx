import { Routes, Route } from 'react-router-dom'
import Login from './Pages/Login'
import Callback from './Pages/Callback'
import Repos from './Pages/Repos'
import ReportAnalysis from './Pages/ReportAnalysis'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Repos />} />
      <Route path="/callback" element={<Callback />} />
      <Route path="/repos" element={<Repos />} />
      <Route path="/analyze/:repoid/:reponame" element={<ReportAnalysis />} />
    </Routes>
  )
}

export default App
