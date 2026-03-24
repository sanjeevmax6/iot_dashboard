import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useLatestAnalysis() {
  return useQuery({
    queryKey: ["analysis", "latest"],
    queryFn: api.analysis.latest,
    retry: false,
  });
}

