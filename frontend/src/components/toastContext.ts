import { createContext, useContext } from 'react'

export interface ToastInput {
  message: string
  actionLabel?: string
  onAction?: () => void
}

export const ToastContext = createContext<(toast: ToastInput) => void>(() => {})

export const useToast = () => useContext(ToastContext)
