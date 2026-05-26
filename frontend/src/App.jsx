import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Navbar   from './components/Navbar'
import Home     from './pages/Home'
import DrawPage from './pages/DrawPage'
import About    from './pages/About'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry:              1,
      refetchOnWindowFocus: false,
    }
  }
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-900">
          <Navbar />
          <Routes>
            <Route path="/"           element={<Home />} />
            <Route path="/lunchtime"  element={<DrawPage />} />
            <Route path="/teatime"    element={<DrawPage />} />
            <Route path="/about"      element={<About />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}