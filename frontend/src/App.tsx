import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { ToastProvider } from './components/Toast'
import { EmptyState } from './components/ui'
import { AccountsPage } from './pages/AccountsPage'
import { FollowUpsPage } from './pages/FollowUpsPage'
import { TodayPage } from './pages/TodayPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<TodayPage />} />
              <Route path="accounts" element={<AccountsPage />} />
              <Route path="follow-ups" element={<FollowUpsPage />} />
              <Route
                path="*"
                element={
                  <EmptyState title="This page doesn’t exist" action={<Link className="font-semibold text-harbor" to="/">Go to Today</Link>} />
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
