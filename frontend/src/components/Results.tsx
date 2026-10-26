import { useEffect, useState, useCallback } from "react";

import {
  Search,
  SlidersHorizontal,
  Download,
  ArrowRight,
  ArrowLeft,
  ChevronDown,
  X,
  Play,
  Pause,
  Square,
  Copy,
  ExternalLink,
  Trash2,
} from "lucide-react";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  ColumnDef,
} from "@tanstack/react-table";

import { api, send } from "../api";

import { Button, Empty, status } from "./ui";
import Exporter from "./Exporter";
export default function Results({ job, meta, run, toExport }: any) {
  const [data, setData] = useState<any>({ items: [], total: 0, stats: {} }),
    [q, setQ] = useState(""),
    [page, setPage] = useState(1),
    [sort, setSort] = useState("name"),
    [desc, setDesc] = useState(false),
    [presence, setPresence] = useState("all"),
    [selected, setSelected] = useState<string[]>([]),
    [card, setCard] = useState<any>(null),
    [visible, setVisible] = useState<string[]>(job.spec.columns),
    [colMenu, setColMenu] = useState(false);
  const load = useCallback(
    () =>
      api(
        `/jobs/${job.id}/results?q=${encodeURIComponent(q)}&page=${page}&sort=${sort}&desc=${desc}&presence=${presence}`,
      ).then(setData),
    [job.id, q, page, sort, desc, presence],
  );
  useEffect(() => {
    load().catch(() => {});
    const t = setInterval(() => load().catch(() => {}), 1500);
    return () => clearInterval(t);
  }, [load]);
  useEffect(() => {
    setVisible(job.spec.columns);
    setPage(1);
    setSelected([]);
  }, [job.id]);
  const columns: ColumnDef<any>[] = [
    {
      id: "select",
      header: () => (
        <input
          aria-label="Выбрать страницу"
          type="checkbox"
          checked={
            !!data.items.length &&
            data.items.every((r: any) => selected.includes(r.id))
          }
          onChange={(e) =>
            setSelected(
              e.target.checked
                ? Array.from(
                    new Set([...selected, ...data.items.map((r: any) => r.id)]),
                  )
                : selected.filter(
                    (id) => !data.items.some((r: any) => r.id === id),
                  ),
            )
          }
        />
      ),
      cell: ({ row }) => (
        <input
          aria-label={"Выбрать " + row.original.name}
          type="checkbox"
          checked={selected.includes(row.original.id)}
          onChange={(e) =>
            setSelected(
              e.target.checked
                ? [...selected, row.original.id]
                : selected.filter((id) => id !== row.original.id),
            )
          }
        />
      ),
      size: 48,
    },
    ...visible.map((k) => ({
      accessorKey: k,
      header: () => (
        <button
          className="sort"
          onClick={() => {
            setSort(k);
            setDesc(sort === k ? !desc : false);
          }}
        >
          {meta.fields[k]}
          {sort === k && <ChevronDown size={13} />}
        </button>
      ),
      cell: ({ row }: any) => {
        const value = row.original[k];
        return k === "name" ? (
          <button
            className="text-button name-cell"
            onClick={() => setCard(row.original)}
          >
            {value}
          </button>
        ) : (
          <span>
            {value == null ? (
              <span className="muted">
                {row.original.field_status[k] === "absent"
                  ? "Нет"
                  : "Неизвестно"}
              </span>
            ) : typeof value === "object" ? (
              JSON.stringify(value)
            ) : (
              String(value)
            )}
          </span>
        );
      },
      size: k === "name" ? 240 : 180,
    })),
  ];
  const table = useReactTable({
    data: data.items,
    columns,
    getCoreRowModel: getCoreRowModel(),
    columnResizeMode: "onChange",
  });
  return (
    <>
      <div className="progress-panel panel">
        <div>
          <h3>{job.name}</h3>
          <p>
            {job.processed} обработано · {job.matched} подходит · {job.excluded}{" "}
            исключено · {job.duplicates} дубликатов · {job.requests} запросов
          </p>
          {job.message && <p role="alert">{job.message}</p>}
        </div>
        <div className="inline">
          {job.status === "running" ? (
            <Button
              onClick={() =>
                run(() => send("/jobs/" + job.id + "/control/pause", {}))
              }
            >
              <Pause size={15} />
              Пауза
            </Button>
          ) : (
            ["paused", "stopped", "failed"].includes(job.status) && (
              <Button
                onClick={() =>
                  run(() => send("/jobs/" + job.id + "/control/resume", {}))
                }
              >
                <Play size={15} />
                Продолжить
              </Button>
            )
          )}
          {["running", "paused"].includes(job.status) && (
            <Button
              onClick={() =>
                run(() => send("/jobs/" + job.id + "/control/stop", {}))
              }
            >
              <Square size={15} />
              Остановить
            </Button>
          )}
          <Button primary onClick={toExport}>
            <Download size={16} />
            Экспорт
          </Button>
        </div>
        <div className="progress-track">
          <div style={{ width: job.progress + "%" }} />
        </div>
      </div>
      <div className="mini-stats">
        {[
          ["Телефоны", "phone"],
          ["Telegram", "telegram"],
          ["Сайты", "website"],
          ["Без сайта", "website_absent"],
          ["Сайт неизвестен", "website_unknown"],
        ].map(([label, k]) => (
          <div key={k}>
            <span>{label}</span>
            <b>{data.stats[k] || 0}</b>
          </div>
        ))}
      </div>
      <div className="results-toolbar">
        <div className="input-icon">
          <Search size={16} />
          <input
            placeholder="Поиск по результатам"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <select
          aria-label="Фильтр по сайту"
          value={presence}
          onChange={(e) => {
            setPresence(e.target.value);
            setPage(1);
          }}
        >
          <option value="all">Все организации</option>
          <option value="present">С сайтом</option>
          <option value="absent">Без сайта</option>
          <option value="unknown">Сайт неизвестен</option>
        </select>
        <Button onClick={() => setColMenu(!colMenu)}>
          <SlidersHorizontal size={16} />
          Колонки
        </Button>
        {selected.length > 0 && (
          <Button
            onClick={() =>
              run(async () => {
                await send("/jobs/" + job.id + "/remove-rows", {
                  ids: selected,
                });
                setSelected([]);
                await load();
              })
            }
          >
            <Trash2 size={15} />
            Удалить {selected.length}
          </Button>
        )}
      </div>
      {colMenu && (
        <div className="column-checks panel">
          {Object.entries(meta.fields).map(([k, v]: any) => (
            <label key={k}>
              <input
                type="checkbox"
                checked={visible.includes(k)}
                onChange={() =>
                  setVisible(
                    visible.includes(k)
                      ? visible.filter((x) => x !== k)
                      : [...visible, k],
                  )
                }
              />
              {v}
            </label>
          ))}
        </div>
      )}
      <div className="table-wrap result-table">
        <table style={{ width: table.getTotalSize() }}>
          <thead>
            {table.getHeaderGroups().map((g) => (
              <tr key={g.id}>
                {g.headers.map((h) => (
                  <th
                    key={h.id}
                    style={{ width: h.getSize(), position: "relative" }}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    <div
                      className="resizer"
                      onMouseDown={h.getResizeHandler()}
                      onTouchStart={h.getResizeHandler()}
                    />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {!data.items.length && (
          <Empty
            title={
              job.status === "running"
                ? "Поиск выполняется…"
                : "Подходящих записей пока нет"
            }
            text="Проверьте фильтры и статус задачи."
          />
        )}
      </div>
      <div className="pagination">
        <span>
          {data.total} записей · выбрано {selected.length}
        </span>
        <div>
          <Button disabled={page === 1} onClick={() => setPage(page - 1)}>
            <ArrowLeft size={15} />
          </Button>
          <span>
            Страница {page} из {Math.max(1, Math.ceil(data.total / 25))}
          </span>
          <Button
            disabled={page * 25 >= data.total}
            onClick={() => setPage(page + 1)}
          >
            <ArrowRight size={15} />
          </Button>
        </div>
      </div>
      {selected.length > 0 && (
        <Exporter
          job={job}
          meta={meta}
          run={run}
          templates={[]}
          selected={selected}
          compact
        />
      )}
      {card && (
        <div className="modal-backdrop" onClick={() => setCard(null)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Карточка организации"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close"
              aria-label="Закрыть карточку"
              onClick={() => setCard(null)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">КАРТОЧКА ОРГАНИЗАЦИИ</span>
            <h2>{card.name}</h2>
            <p>
              {card.category} · {card.city}
            </p>
            <div className="card-fields">
              {Object.entries(meta.fields).map(([k, v]: any) => (
                <div key={k}>
                  <small>{v}</small>
                  <span>
                    {card[k] == null
                      ? "Неизвестно"
                      : typeof card[k] === "object"
                        ? JSON.stringify(card[k])
                        : String(card[k])}
                  </span>
                </div>
              ))}
            </div>
            <div className="inline">
              <Button
                onClick={() =>
                  run(() =>
                    navigator.clipboard.writeText(
                      [card.phone, card.email, card.website, card.telegram]
                        .filter(Boolean)
                        .join("\n"),
                    ),
                  )
                }
              >
                <Copy size={15} />
                Контакты
              </Button>
              {card.url && (
                <a
                  className="button"
                  href={card.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Открыть в 2ГИС
                  <ExternalLink size={15} />
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
