import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";

export function useLatestAnalysis() {
  return useQuery({
    queryKey: ["analysis", "latest"],
    queryFn: api.analysis.latest,
    retry: false,
  });
}

export function useRunAnalysis() {
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const mutation = useMutation({
    mutationFn: api.analysis.run,
    onSuccess: (data) => setJobId(data.job_id),
  });

  const { data: statusData } = useQuery({
    queryKey: ["analysis", "status", jobId],
    queryFn: () => api.analysis.status(jobId!),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (
      statusData?.status === "complete" ||
      statusData?.status === "error"
    ) {
      setJobId(null);
      void queryClient.invalidateQueries({ queryKey: ["analysis", "latest"] });
    }
  }, [statusData?.status, queryClient]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const isRunning =
    mutation.isPending ||
    statusData?.status === "pending" ||
    statusData?.status === "running";

  return { run: mutation.mutate, isRunning, jobStatus: statusData?.status };
}
