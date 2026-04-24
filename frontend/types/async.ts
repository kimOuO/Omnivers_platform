export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  status: AsyncStatus;
  error: ApiError | null;
  refetch: () => void;
}

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  details?: unknown;
}
