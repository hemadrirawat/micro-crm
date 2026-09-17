import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { CheckCircle2, X } from 'lucide-react'
import { ToastContext, type ToastInput } from './toastContext'

interface ToastState extends ToastInput {
  id: number
}


export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const show = useCallback((input: ToastInput) => {
    window.clearTimeout(timer.current)
    setToast({ ...input, id: Date.now() })
    timer.current = window.setTimeout(() => setToast(null), 6000)
  }, [])

  useEffect(() => () => window.clearTimeout(timer.current), [])

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
        {toast && (
          <div
            key={toast.id}
            className="pointer-events-auto flex items-center gap-3 rounded-xl bg-ink px-4 py-2.5 text-sm text-white shadow-lg"
          >
            <CheckCircle2 className="size-4 text-checkin-soft" aria-hidden />
            <span>{toast.message}</span>
            {toast.onAction && (
              <button
                type="button"
                className="font-semibold text-harbor-soft underline underline-offset-2"
                onClick={() => {
                  toast.onAction?.()
                  setToast(null)
                }}
              >
                {toast.actionLabel ?? 'Undo'}
              </button>
            )}
            <button type="button" aria-label="Dismiss" onClick={() => setToast(null)} className="text-white/60">
              <X className="size-4" />
            </button>
          </div>
        )}
      </div>
    </ToastContext.Provider>
  )
}
