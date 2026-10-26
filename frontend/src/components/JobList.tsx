import { Search, ChevronRight, Copy, Trash2 } from "lucide-react";

import { api } from "../api";

import { status, date } from "./ui";
export default function JobList({ jobs, open, run, onRepeat }: any) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Название задачи</th>
            <th>География</th>
            <th>Статус</th>
            <th>Результаты</th>
            <th>Создана</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {jobs.map((j: any) => (
            <tr key={j.id}>
              <td>
                <button className="job-name" onClick={() => open(j.id)}>
                  <span className="row-icon">
                    <Search size={16} />
                  </span>
                  <span>
                    {j.name}
                    <small>
                      {j.spec.categories.slice(0, 2).join(", ")}
                      {j.mode === "demo" ? " · демо" : ""}
                    </small>
                  </span>
                </button>
              </td>
              <td>{j.spec.cities.map((c: any) => c.name).join(", ")}</td>
              <td>
                <span className={"status " + j.status}>
                  <i />
                  {status[j.status]}
                </span>
              </td>
              <td className="number">{j.matched}</td>
              <td className="muted">{date(j.created_at)}</td>
              <td>
                <div className="row-actions">
                  <button
                    title="Повторить с настройками"
                    aria-label="Повторить с настройками"
                    onClick={() => onRepeat(j)}
                  >
                    <Copy size={16} />
                  </button>
                  <button
                    title="Удалить задачу"
                    aria-label="Удалить задачу"
                    onClick={() => {
                      if (confirm("Удалить задачу и её результаты?"))
                        run(() => api("/jobs/" + j.id, { method: "DELETE" }));
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                  <button
                    aria-label="Открыть результаты"
                    onClick={() => open(j.id)}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
