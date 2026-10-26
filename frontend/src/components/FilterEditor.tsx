import { Plus, X } from "lucide-react";

import { Button } from "./ui";
export default function FilterEditor({
  group,
  onChange,
  fields,
  depth = 0,
  available = {},
}: any) {
  const update = (i: number, c: any) =>
    onChange({
      ...group,
      conditions: group.conditions.map((v: any, n: number) =>
        n === i ? c : v,
      ),
    });
  return (
    <div className="filter-group">
      <div className="filter-group-head">
        <select
          aria-label="Логика группы"
          value={group.logic}
          onChange={(e) => onChange({ ...group, logic: e.target.value })}
        >
          <option value="AND">Все условия · И</option>
          <option value="OR">Любое условие · ИЛИ</option>
        </select>
        <span className="muted">
          {depth ? "Группа условий" : "Организация подходит, если выполнены"}
        </span>
      </div>
      {group.conditions.map((c: any, i: number) =>
        c.conditions ? (
          <div key={i} className="nested">
            <FilterEditor
              group={c}
              onChange={(v: any) => update(i, v)}
              fields={fields}
              depth={depth + 1}
              available={available}
            />
            <button
              aria-label="Удалить группу"
              onClick={() =>
                onChange({
                  ...group,
                  conditions: group.conditions.filter(
                    (_: any, n: number) => n !== i,
                  ),
                })
              }
            >
              <X size={16} />
            </button>
          </div>
        ) : (
          <div className="condition" key={i}>
            <select
              aria-label="Поле фильтра"
              value={c.field}
              onChange={(e) => update(i, { ...c, field: e.target.value })}
            >
              {Object.entries(fields)
                .filter(
                  ([k]) =>
                    !["field_status", "fetched_at", "source"].includes(k),
                )
                .map(([k, v]: any) => (
                  <option key={k} value={k}>
                    {v}
                    {available[k] === false ? " · недоступно" : ""}
                  </option>
                ))}
            </select>
            <select
              aria-label="Условие"
              value={c.op}
              onChange={(e) => update(i, { ...c, op: e.target.value })}
            >
              {Object.entries({
                present: "Есть",
                absent: "Нет",
                contains: "Содержит",
                not_contains: "Не содержит",
                eq: "Равно",
                gte: "Не меньше",
                lte: "Не больше",
                https: "HTTPS",
                domain: "Домен",
                not_domain: "Кроме домена",
              }).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            {!["present", "absent", "https"].includes(c.op) && (
              <input
                aria-label="Значение условия"
                value={c.value ?? ""}
                type={["gte", "lte"].includes(c.op) ? "number" : "text"}
                onChange={(e) => update(i, { ...c, value: e.target.value })}
              />
            )}
            <button
              aria-label="Удалить условие"
              onClick={() =>
                onChange({
                  ...group,
                  conditions: group.conditions.filter(
                    (_: any, n: number) => n !== i,
                  ),
                })
              }
            >
              <X size={16} />
            </button>
          </div>
        ),
      )}
      <div className="filter-add">
        <Button
          onClick={() =>
            onChange({
              ...group,
              conditions: [
                ...group.conditions,
                { field: "website", op: "absent", value: null },
              ],
            })
          }
        >
          <Plus size={14} />
          Условие
        </Button>
        {depth < 3 && (
          <Button
            onClick={() =>
              onChange({
                ...group,
                conditions: [
                  ...group.conditions,
                  { logic: "OR", conditions: [] },
                ],
              })
            }
          >
            <Plus size={14} />
            Группа
          </Button>
        )}
      </div>
    </div>
  );
}
