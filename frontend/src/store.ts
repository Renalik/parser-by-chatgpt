import { create } from "zustand";
export const initialSpec = {
  name: "Новый поиск",
  mode: "live",
  cities: [] as { name: string; region_id: string }[],
  categories: [] as string[],
  excluded_categories: [] as string[],
  keyword: "",
  point: null as string | null,
  radius: null as number | null,
  filters: { logic: "AND", conditions: [] } as any,
  unknown: "exclude",
  dedup: "branch_id",
  limit: 100,
  request_limit: 100,
  requests_per_second: 1,
  columns: ["name", "city", "phone", "website", "url"],
  score_weights: { phone: 1, email: 1, website: 1, telegram: 1, whatsapp: 1 },
};
export const useStore = create<{
  page: string;
  setPage: (s: string) => void;
  spec: typeof initialSpec;
  setSpec: (x: Partial<typeof initialSpec>) => void;
  jobId: string;
  setJob: (s: string) => void;
}>((set) => ({
  page: "Главная",
  setPage: (page) => set({ page }),
  spec: initialSpec,
  setSpec: (x) => set((s) => ({ spec: { ...s.spec, ...x } })),
  jobId: "",
  setJob: (jobId) => set({ jobId }),
}));
