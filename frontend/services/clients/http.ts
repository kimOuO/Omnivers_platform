// HTTP client wrapper. Server- and client-safe (uses native fetch).
// Only place in the codebase that should call `fetch` directly.
//
// Aligned with Omniver-RAN (Django) backend conventions:
//   - ALL endpoints are POST (backend_rule.md §7-2)
//   - Response envelope: { success: boolean, message: string, data: T, errors?: object }
//   - URL format: /api/v0.1/{System}/{Module}/{Component}/{Element}

import { API_BASE_URL, DEFAULT_FETCH_TIMEOUT_MS } from '@/config';
import type { ApiError } from '@/types';

interface PostOptions {
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
  signal?: AbortSignal;
}

interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
  errors?: unknown;
}

function toApiError(message: string, status?: number, details?: unknown): ApiError {
  return { message, status, details };
}

export async function post<T>(path: string, options: PostOptions = {}): Promise<T> {
  const { body = {}, headers = {}, timeoutMs = DEFAULT_FETCH_TIMEOUT_MS, signal } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const externalAbort = () => controller.abort();
  signal?.addEventListener('abort', externalAbort);

  try {
    // eslint-disable-next-line no-restricted-syntax
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: 'no-store',
    });

    const raw = res.status === 204 ? null : await res.json().catch(() => null);

    if (!res.ok) {
      throw toApiError(
        (raw as Envelope<unknown> | null)?.message || `HTTP ${res.status} ${res.statusText}`,
        res.status,
        raw,
      );
    }

    const envelope = raw as Envelope<T> | null;
    if (envelope && typeof envelope === 'object' && 'success' in envelope) {
      if (!envelope.success) {
        throw toApiError(envelope.message || 'Request failed', res.status, envelope.errors);
      }
      return envelope.data;
    }
    return raw as T;
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw toApiError('Request timed out', 408);
    }
    if (typeof err === 'object' && err !== null && 'message' in err) {
      throw err as ApiError;
    }
    throw toApiError('Unknown request error');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', externalAbort);
  }
}
