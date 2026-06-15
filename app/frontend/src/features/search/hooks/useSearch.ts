import { useMutation } from '@tanstack/react-query';
import { searchApi } from '../api/search.api';

/** Natural-language plan search (POST /search). Triggered on submit, not on type. */
export const useSearch = () =>
  useMutation({ mutationFn: (query: string) => searchApi.query(query) });
