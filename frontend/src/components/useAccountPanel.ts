import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

/** The open account lives in the URL (?account=cust_001) so it survives reloads and can be linked. */
export function useAccountPanel() {
  const [params, setParams] = useSearchParams()
  const accountId = params.get('account')

  const open = useCallback(
    (id: string) =>
      setParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('account', id)
        return next
      }),
    [setParams],
  )

  const close = useCallback(
    () =>
      setParams((prev) => {
        const next = new URLSearchParams(prev)
        next.delete('account')
        return next
      }),
    [setParams],
  )

  return { accountId, open, close }
}
