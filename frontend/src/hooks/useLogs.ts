import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

interface LogFilters {
  page: number;
  page_size: number;
  machine_id?: string;
  status?: string;
}

export function useLogs(filters: LogFilters) {
  return useQuery({
    queryKey: ["logs", filters],
    queryFn: () => api.logs.list(filters),
  });
}
