import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '../components/layout/ProtectedRoute'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { AuthorLayout } from '../layouts/AuthorLayout'
import { AdminLayout } from '../layouts/AdminLayout'
import { BooksPage } from '../features/books/pages/BooksPage'
import { TicketsPage } from '../features/tickets/pages/TicketsPage'
import { AdminDashboard } from '../features/admin/pages/AdminDashboard'
import { NotFoundPage } from '../pages/NotFoundPage'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute allowedRoles={['author']} />,
    children: [
      {
        path: '/author',
        element: <AuthorLayout />,
        children: [
          { index: true, element: <Navigate to="/author/books" replace /> },
          { path: 'books', element: <BooksPage /> },
          { path: 'tickets', element: <TicketsPage /> },
        ],
      },
    ],
  },
  {
    element: <ProtectedRoute allowedRoles={['admin']} />,
    children: [
      {
        path: '/admin',
        element: <AdminLayout />,
        children: [
          { index: true, element: <AdminDashboard /> },
          { path: 'tickets', element: <AdminDashboard /> },
        ],
      },
    ],
  },
  { path: '/', element: <Navigate to="/author" replace /> },
  { path: '*', element: <NotFoundPage /> },
])
