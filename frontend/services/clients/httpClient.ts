import { post } from './http';

export const omniverseClient = {
  post: async <T,>(path: string, body?: unknown): Promise<T> => {
    return post<T>(path, { body });
  },
};
