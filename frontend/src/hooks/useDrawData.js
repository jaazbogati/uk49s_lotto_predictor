import { useQuery } from '@tanstack/react-query'
import { getLatest, getStats, getNumbers, getPredictions } from '../utils/api'

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