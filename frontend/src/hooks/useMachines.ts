import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function useMachines() {
  return useQuery({
    queryKey: ["machines"],
    queryFn: api.machines.list,
  });
}
