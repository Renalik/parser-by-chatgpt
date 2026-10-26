import { useEffect, useState } from "react";

import { Download, Check, Save, FileDown, GripVertical } from "lucide-react";

import { api, send } from "../api";

import { Button } from "./ui";
export default function Exporter({
  job,
  meta,
  run,
  templates,
  selected,
  compact = false,
}: any) {
  const [format, setFormat] = useState("xlsx"),
    [columns, setColumns] = useState<string[]>(job.spec.columns),
    [headers, setHeaders] = useState<Record<string, string>>({}),
    [delimiter, setDelimiter] = useState(";"),
    [bom, setBom] = useState(true),
    [includeHeaders, setIncludeHeaders] = useState(true),
    [empty, setEmpty] = useState("blank"),
    [required, setRequired] = useState<string[]>([]),
    [width, setWidth] = useState(24),
    [metadata, setMetadata] = useState(true),
    [preview, setPreview] = useState<any[]>([]);
  useEffect(() => {
    setColumns(job.spec.columns);
    api("/jobs/" + job.id + "/results?size=3")
      .then((d) => setPreview(d.items))
      .catch(() => {});
  }, [job.id]);
  const spec = () => ({
    format,
    columns,
    headers,
    delimiter,
    bom,
    include_headers: includeHeaders,
    empty,
    required,
    width,
    metadata,
    ...(selected ? { ids: selected } : {}),
  });
  const download = () =>
    run(async () => {
      const r = await fetch("/api/jobs/" + job.id + "/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(spec()),
      });
      if (!r.ok) {
        const d = await r.json();
        throw new Error(d.detail);
      }
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `organizations-${job.id.slice(0, 8)}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  const move = (from: number, to: number) => {
    if (to < 0 || to >= columns.length) return;
    const next = [...columns];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setColumns(next);
  };
  return (
    <div className="panel export-panel">
      <div className="section-heading">
        <div>
          <h2>
            {selected
              ? `Экспорт ${selected.length} выбранных записей`
              : "Конструктор экспорта"}
          </h2>
          <p>Выберите поля, порядок и формат файла.</p>
        </div>
        <FileDown size={22} />
      </div>
      <div className="format-options">
        {["xlsx", "csv", "json"].map((f) => (
          <button
            className={format === f ? "chosen" : ""}
            key={f}
            onClick={() => setFormat(f)}
          >
            <FileDown size={18} />
            <b>{f.toUpperCase()}</b>
            <small>
              {
                {
                  xlsx: "Таблица Excel",
                  csv: "Универсальная таблица",
                  json: "Структура данных",
                }[f]
              }
            </small>
            {format === f && <Check size={16} />}
          </button>
        ))}
      </div>
      <label>Колонки файла</label>
      <div className="column-checks">
        {Object.entries(meta.fields).map(([k, v]: any) => (
          <label key={k}>
            <input
              type="checkbox"
              checked={columns.includes(k)}
              onChange={() =>
                setColumns(
                  columns.includes(k)
                    ? columns.filter((x) => x !== k)
                    : [...columns, k],
                )
              }
            />
            {v}
          </label>
        ))}
      </div>
      <div className="inline">
        <Button onClick={() => setColumns(Object.keys(meta.fields))}>
          Выбрать все
        </Button>
        <Button
          onClick={() => {
            setColumns(job.spec.columns);
            setHeaders({});
          }}
        >
          Сбросить
        </Button>
      </div>
      <div className="ordered-columns">
        {columns.map((k, i) => (
          <div
            className="ordered-column"
            draggable
            onDragStart={(e) => e.dataTransfer.setData("text/plain", String(i))}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              move(Number(e.dataTransfer.getData("text/plain")), i);
            }}
            key={k}
          >
            <GripVertical size={16} />
            <span>{String(i + 1).padStart(2, "0")}</span>
            <input
              aria-label={"Заголовок " + meta.fields[k]}
              value={headers[k] ?? meta.fields[k]}
              onChange={(e) => setHeaders({ ...headers, [k]: e.target.value })}
            />
            <button
              aria-label={"Поднять " + meta.fields[k]}
              onClick={() => move(i, i - 1)}
            >
              ↑
            </button>
            <button
              aria-label={"Опустить " + meta.fields[k]}
              onClick={() => move(i, i + 1)}
            >
              ↓
            </button>
            <label title="Исключать записи с пустым полем">
              <input
                type="checkbox"
                checked={required.includes(k)}
                onChange={() =>
                  setRequired(
                    required.includes(k)
                      ? required.filter((x) => x !== k)
                      : [...required, k],
                  )
                }
              />
              Обязательно
            </label>
          </div>
        ))}
      </div>
      <div className="form-grid">
        <label>
          Пустые значения
          <select value={empty} onChange={(e) => setEmpty(e.target.value)}>
            <option value="blank">Пустая ячейка</option>
            <option value="dash">Прочерк</option>
            <option value="null">Текст null</option>
          </select>
        </label>
        {format === "csv" && (
          <>
            <label>
              Разделитель
              <select
                value={delimiter}
                onChange={(e) => setDelimiter(e.target.value)}
              >
                <option value=";">Точка с запятой</option>
                <option value=",">Запятая</option>
                <option value={"\t"}>Табуляция</option>
              </select>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={bom}
                onChange={(e) => setBom(e.target.checked)}
              />
              UTF-8 с BOM
            </label>
          </>
        )}
        {format === "xlsx" && (
          <label>
            Ширина столбцов
            <input
              type="number"
              min="8"
              max="80"
              value={width}
              onChange={(e) => setWidth(Number(e.target.value))}
            />
          </label>
        )}
        {format !== "json" ? (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeHeaders}
              onChange={(e) => setIncludeHeaders(e.target.checked)}
            />
            Включать заголовки
          </label>
        ) : (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={metadata}
              onChange={(e) => setMetadata(e.target.checked)}
            />
            Метаданные доступности полей
          </label>
        )}
      </div>
      {format === "json" && (
        <p className="muted">
          В JSON отсутствующие значения всегда сохраняются как null.
        </p>
      )}
      {!compact && preview.length > 0 && (
        <>
          <h3>Предпросмотр · первые записи</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {columns.map((k) => (
                    <th key={k}>{headers[k] || meta.fields[k]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((r: any) => (
                  <tr key={r.id}>
                    {columns.map((k) => (
                      <td key={k}>
                        {r[k] == null
                          ? "—"
                          : typeof r[k] === "object"
                            ? JSON.stringify(r[k])
                            : String(r[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <div className="wizard-footer">
        <div className="inline">
          <Button
            onClick={() =>
              run(async () => {
                const name = prompt("Название пресета экспорта");
                if (name)
                  await send("/templates", {
                    name,
                    kind: "export",
                    value: spec(),
                  });
              })
            }
          >
            <Save size={15} />
            Сохранить пресет
          </Button>
          {templates.some((t: any) => t.kind === "export") && (
            <select
              aria-label="Пресет экспорта"
              value=""
              onChange={(e) => {
                const v = templates.find(
                  (t: any) => t.id === e.target.value,
                ).value;
                setColumns(v.columns);
                setHeaders(v.headers);
                setFormat(v.format);
                setDelimiter(v.delimiter);
                setBom(v.bom);
                setIncludeHeaders(v.include_headers);
                setEmpty(v.empty);
                setRequired(v.required);
                setWidth(v.width);
                setMetadata(v.metadata);
              }}
            >
              <option value="">Загрузить пресет</option>
              {templates
                .filter((t: any) => t.kind === "export")
                .map((t: any) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
            </select>
          )}
        </div>
        <Button
          primary
          disabled={
            !columns.length ||
            (!meta.license.export_allowed && job.mode === "live")
          }
          onClick={download}
        >
          <Download size={16} />
          Скачать {format.toUpperCase()}
        </Button>
      </div>
      {job.mode === "live" && !meta.license.export_allowed && (
        <p>Для экспорта требуется разрешение вашей лицензии в настройках.</p>
      )}
    </div>
  );
}
