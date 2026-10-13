import { useEffect, useState } from 'react'
import { apiClient, type ApiClient, type ErrorResponse } from './api/client'

const CONNECTION_FAILED =
  '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'
const UNEXPECTED_RESPONSE =
  '서버가 예상하지 못한 응답을 보냈습니다. 잠시 후 다시 시도해 주세요.'

type HealthState =
  | { kind: 'loading' }
  | { kind: 'ok' }
  | { kind: 'error'; message: string; requestId?: string }

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as ErrorResponse).message === 'string' &&
    typeof (value as ErrorResponse).request_id === 'string'
  )
}

async function checkHealth(client: ApiClient): Promise<HealthState> {
  try {
    const { data, error } = await client.GET('/health')
    if (data) {
      return { kind: 'ok' }
    }
    if (isErrorResponse(error)) {
      return {
        kind: 'error',
        message: error.message,
        requestId: error.request_id,
      }
    }
    return { kind: 'error', message: UNEXPECTED_RESPONSE }
  } catch {
    return { kind: 'error', message: CONNECTION_FAILED }
  }
}

type AppProps = {
  client?: ApiClient
}

function App({ client = apiClient }: AppProps) {
  const [health, setHealth] = useState<HealthState>({ kind: 'loading' })

  useEffect(() => {
    let ignore = false
    void checkHealth(client).then((state) => {
      if (!ignore) {
        setHealth(state)
      }
    })
    return () => {
      ignore = true
    }
  }, [client])

  return (
    <main>
      <h1>CodeMap</h1>
      {health.kind === 'loading' && <p>서버 상태를 확인하는 중입니다…</p>}
      {health.kind === 'ok' && <p>API 정상 · DB 정상</p>}
      {health.kind === 'error' && (
        <>
          <p role="alert">{health.message}</p>
          {health.requestId && <p>요청 ID: {health.requestId}</p>}
        </>
      )}
    </main>
  )
}

export default App
