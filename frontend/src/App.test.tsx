import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { createApiClient } from './api/client'

const BASE_URL = 'https://api.example.test'

function clientReturning(respond: (request: Request) => Promise<Response>) {
  const requests: Request[] = []
  const client = createApiClient({
    baseUrl: BASE_URL,
    fetch: (input: Request) => {
      requests.push(input)
      return respond(input)
    },
  })
  return { client, requests }
}

function json(body: unknown, status: number) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('App 헬스 상태 표시', () => {
  it('API와 DB가 정상이면 정상이라고 표시한다', async () => {
    const { client, requests } = clientReturning(() =>
      json({ status: 'ok', database: 'ok' }, 200),
    )
    render(<App client={client} />)

    expect(await screen.findByText('API 정상 · DB 정상')).toBeInTheDocument()
    expect(requests[0]?.url).toBe(`${BASE_URL}/health`)
  })

  it('에러 응답이면 서버의 message와 request_id를 보여준다', async () => {
    const { client } = clientReturning(() =>
      json(
        {
          code: 'DATABASE_UNAVAILABLE',
          message:
            '데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.',
          request_id: 'req-123',
        },
        503,
      ),
    )
    render(<App client={client} />)

    expect(
      await screen.findByText(
        '데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(/req-123/)).toBeInTheDocument()
  })

  it('서버에 닿지 못하면 연결 실패를 안내한다', async () => {
    const { client } = clientReturning(() =>
      Promise.reject(new TypeError('Failed to fetch')),
    )
    render(<App client={client} />)

    expect(
      await screen.findByText(
        '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.',
      ),
    ).toBeInTheDocument()
  })
})
