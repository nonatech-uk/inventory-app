import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Shell from './components/layout/Shell.tsx'
import { usePageTracking } from './hooks/usePageTracking.ts'
import Dashboard from './pages/Dashboard.tsx'
import Locations from './pages/Locations.tsx'
import Items from './pages/Items.tsx'
import ItemDetail from './pages/ItemDetail.tsx'
import AddItem from './pages/AddItem.tsx'
import Media from './pages/Media.tsx'
import Search from './pages/Search.tsx'
import Amazon from './pages/Amazon.tsx'
import Ebay from './pages/Ebay.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <PageTracker />
      <Shell>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/locations" element={<Locations />} />
          <Route path="/items" element={<Items />} />
          <Route path="/items/:id" element={<ItemDetail />} />
          <Route path="/add" element={<AddItem />} />
          <Route path="/media" element={<Media />} />
          <Route path="/search" element={<Search />} />
          <Route path="/amazon" element={<Amazon />} />
          <Route path="/ebay" element={<Ebay />} />
          <Route path="*" element={<div className="text-text-secondary">Page not found</div>} />
        </Routes>
      </Shell>
    </BrowserRouter>
  )
}

function PageTracker() {
  usePageTracking()
  return null
}
