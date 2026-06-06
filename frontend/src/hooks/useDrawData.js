import { useQuery } from '@tanstack/react-query'
import { getLatest, getStats, getNumbers, getPredictions } from '../utils/api'
import { useMutation } from '@tanstack/react-query'
import { logPredictions } from '../utils/api'

export function useLogPredictions() {
  return useMutation({
    mutationFn: (body) => logPredictions(body).then(r => r.data)
  })
}

export function useLatest(limit = 20) {
  return useQuery({
    queryKey:  ['latest', limit],
    queryFn:   () => getLatest(limit).then(r => r.data),
    staleTime: 5 * 60 * 1000,   // Consider fresh for 5 minutes
  })
}

export function useStats(drawType) {
  return useQuery({
    queryKey:  ['stats', drawType],
    queryFn:   () => getStats(drawType).then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled:   !!drawType,
  })
}

export function useNumbers(drawType) {
  return useQuery({
    queryKey:  ['numbers', drawType],
    queryFn:   () => getNumbers(drawType).then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled:   !!drawType,
  })
}

export function usePredictions(drawType, enabled = false, nTickets = 5) {
  return useQuery({
    queryKey:  ['predictions', drawType, nTickets],
    queryFn:   () => getPredictions(drawType, nTickets).then(r => r.data),
    enabled:   enabled && !!drawType,   // Only runs when user clicks Generate
    staleTime: 0,                       // Always fresh — GA is random each run
    retry:     1,
  })
}

// In useDrawData.js — add staleTime: 0 to track record query
export function useTrackRecord(drawType) {
  return useQuery({
    queryKey:  ['track-record', drawType],
    queryFn:   () => api.get(`/track-record/${drawType}`).then(r => r.data),
    staleTime: 0,        // ← always refetch, never serve stale
    refetchOnWindowFocus: true,
  })
}