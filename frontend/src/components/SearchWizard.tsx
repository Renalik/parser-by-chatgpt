import { useEffect, useState } from "react";

import {
  Search,
  Plus,
  ArrowRight,
  ArrowLeft,
  MapPin,
  Check,
  ChevronRight,
  X,
  Play,
  Save,
  Database,
  Info,
  Layers,
  CircleHelp,
} from "lucide-react";

import { api, send } from "../api";
import { useStore } from "../store";
import { Button } from "./ui";
import FilterEditor from "./FilterEditor";
export default function SearchWizard({
  meta,
  run,
  busy,
  onCreated,
  saveTemplate,
  templates,
  standalone,
}: any) {
  const { spec, setSpec } = useStore();
  const [step, setStep] = useState(0),
    [city, setCity] = useState(""),
    [suggestions, setSuggestions] = useState<any[]>([]),
    [catQuery, setCatQuery] = useState(""),
    [custom, setCustom] = useState(""),
    [catalog, setCatalog] = useState<any[]>([]);
  useEffect(() => {
    setStep(standalone === "Категории" ? 1 : standalone === "Фильтры" ? 2 : 0);
  }, [standalone]);
  const categories = Array.from(
    new Set([...meta.categories, ...spec.categories]),
  );
  const steps = ["География", "Категории", "Фильтры", "Результат"];
  const toggle = (c: string) =>
    setSpec({
      categories: spec.categories.includes(c)
        ? spec.categories.filter((v) => v !== c)
        : [...spec.categories, c],
    });
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">НОВАЯ ПОИСКОВАЯ ЗАДАЧА</div>
        <div className="heading-row">
          <div>
            <h1>Найдите свой бизнес</h1>
            <p>Настройте поиск под вашу задачу — шаг за шагом.</p>
          </div>
          <Button
            onClick={saveTemplate}
            disabled={!spec.cities.length || !spec.categories.length}
          >
            <Save size={16} />
            Сохранить шаблон
          </Button>
        </div>
      </div>
      <div className="wizard-steps">
        {steps.map((s, i) => (
          <button
            className={step === i ? "current" : step > i ? "done" : ""}
            key={s}
            onClick={() => setStep(i)}
          >
            <span>
              {step > i ? <Check size={15} /> : String(i + 1).padStart(2, "0")}
            </span>
            {s}
            {i < 3 && <ChevronRight size={16} />}
          </button>
        ))}
      </div>
      <div className="wizard-layout">
        <div className="panel wizard-body">
          <div className="section-heading">
            <div>
              <h2>{steps[step]}</h2>
              <p>
                {
                  [
                    "Где искать организации?",
                    "Выберите направления бизнеса",
                    "Оставьте только подходящие организации",
                    "Последние настройки перед запуском",
                  ][step]
                }
              </p>
            </div>
            <span className="muted">Шаг {step + 1} из 4</span>
          </div>
          {step === 0 && (
            <>
              <label>
                Название задачи
                <input
                  value={spec.name}
                  onChange={(e) => setSpec({ name: e.target.value })}
                />
              </label>
              <label>Города и регионы</label>
              <div className="inline">
                <div className="input-icon">
                  <MapPin size={17} />
                  <input
                    placeholder="Например, Москва"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter")
                        run(async () =>
                          setSuggestions(
                            await api("/regions?q=" + encodeURIComponent(city)),
                          ),
                        );
                    }}
                  />
                </div>
                <Button
                  disabled={city.length < 2 || !meta.capabilities.connected}
                  onClick={() =>
                    run(async () =>
                      setSuggestions(
                        await api("/regions?q=" + encodeURIComponent(city)),
                      ),
                    )
                  }
                >
                  Найти
                </Button>
              </div>
              {suggestions.length > 0 && (
                <div className="suggestions">
                  {suggestions.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        if (
                          !spec.cities.some((v) => v.region_id === String(c.id))
                        )
                          setSpec({
                            cities: [
                              ...spec.cities,
                              { name: c.name, region_id: String(c.id) },
                            ],
                          });
                        setSuggestions([]);
                        setCity("");
                      }}
                    >
                      <MapPin size={15} />
                      {c.name}
                      <Plus size={15} />
                    </button>
                  ))}
                </div>
              )}
              <div className="chips">
                {spec.cities.map((c) => (
                  <span className="chip" key={c.region_id}>
                    <MapPin size={14} />
                    {c.name}
                    <button
                      aria-label={"Убрать " + c.name}
                      onClick={() =>
                        setSpec({
                          cities: spec.cities.filter(
                            (v) => v.region_id !== c.region_id,
                          ),
                        })
                      }
                    >
                      <X size={13} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="form-grid">
                <label>
                  Центр поиска · необязательно
                  <input
                    placeholder="37.6176,55.7558 — долгота,широта"
                    value={spec.point || ""}
                    onChange={(e) => setSpec({ point: e.target.value || null })}
                  />
                </label>
                <label>
                  Радиус, км
                  <input
                    type="number"
                    min="0.001"
                    max="40"
                    value={spec.radius ? spec.radius / 1000 : ""}
                    onChange={(e) =>
                      setSpec({
                        radius: e.target.value
                          ? Number(e.target.value) * 1000
                          : null,
                      })
                    }
                  />
                </label>
              </div>
              <div className="help-box">
                <Info size={17} />
                <span>
                  Город выбирается из справочника источника. Точные границы
                  районов, полигоны и исключаемые зоны пока недоступны.
                </span>
              </div>
              {templates.filter((t: any) => t.kind === "search").length > 0 && (
                <label>
                  Загрузить шаблон
                  <select
                    value=""
                    onChange={(e) =>
                      setSpec(
                        templates.find((t: any) => t.id === e.target.value)
                          .value,
                      )
                    }
                  >
                    <option value="">Выберите шаблон</option>
                    {templates
                      .filter((t: any) => t.kind === "search")
                      .map((t: any) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                  </select>
                </label>
              )}
            </>
          )}
          {step === 1 && (
            <>
              <div className="input-icon">
                <Search size={17} />
                <input
                  placeholder="Найти категорию"
                  value={catQuery}
                  onChange={(e) => setCatQuery(e.target.value)}
                />
              </div>
              <div className="select-all">
                <span>{spec.categories.length} выбрано</span>
                <button
                  onClick={() =>
                    setSpec({
                      categories: spec.categories.length ? [] : meta.categories,
                    })
                  }
                >
                  {spec.categories.length ? "Снять выбор" : "Выбрать все"}
                </button>
              </div>
              <div className="category-grid">
                {categories
                  .filter((c: any) =>
                    c.toLowerCase().includes(catQuery.toLowerCase()),
                  )
                  .map((c: any) => (
                    <label
                      className={
                        "category-option " +
                        (spec.categories.includes(c) ? "selected" : "")
                      }
                      key={c}
                    >
                      <input
                        type="checkbox"
                        checked={spec.categories.includes(c)}
                        onChange={() => toggle(c)}
                      />
                      {c}
                    </label>
                  ))}
              </div>
              <label>Своя категория / поиск точной рубрики</label>
              <div className="inline">
                <input
                  value={custom}
                  placeholder="Название рубрики"
                  onChange={(e) => setCustom(e.target.value)}
                />
                <Button
                  disabled={!custom}
                  onClick={() => {
                    toggle(custom);
                    setCustom("");
                  }}
                >
                  <Plus size={15} />
                  Добавить
                </Button>
                <Button
                  disabled={!custom || !spec.cities.length}
                  onClick={() =>
                    run(async () =>
                      setCatalog(
                        await api(
                          "/categories?q=" +
                            encodeURIComponent(custom) +
                            "&region_id=" +
                            encodeURIComponent(spec.cities[0].region_id),
                        ),
                      ),
                    )
                  }
                >
                  Справочник
                </Button>
              </div>
              {catalog.length > 0 && (
                <div className="chips">
                  {catalog.map((c) => (
                    <button
                      className="chip"
                      key={c.id}
                      onClick={() => toggle(c.name)}
                    >
                      {c.name}
                      <Plus size={14} />
                    </button>
                  ))}
                </div>
              )}
              <label>
                Исключить категории · через запятую
                <input
                  value={spec.excluded_categories.join(", ")}
                  onChange={(e) =>
                    setSpec({
                      excluded_categories: e.target.value
                        .split(",")
                        .map((s) => s.trim()),
                    })
                  }
                />
              </label>
              <label>
                Ключевые слова
                <input
                  placeholder="Необязательно"
                  value={spec.keyword}
                  onChange={(e) => setSpec({ keyword: e.target.value })}
                />
              </label>
            </>
          )}
          {step === 2 && (
            <>
              <FilterEditor
                group={spec.filters}
                onChange={(filters: any) => setSpec({ filters })}
                fields={meta.fields}
                available={meta.capabilities.fields || {}}
              />
              <label>
                Если значение неизвестно
                <select
                  value={spec.unknown}
                  onChange={(e) => setSpec({ unknown: e.target.value })}
                >
                  <option value="exclude">
                    Исключать из подходящих результатов
                  </option>
                  <option value="include">
                    Включать, сохраняя статус «неизвестно»
                  </option>
                </select>
              </label>
              <div className="help-box">
                <CircleHelp size={17} />
                <span>
                  Отсутствие доступа к контактам не означает, что у организации
                  нет телефона или сайта. Фильтры недоступных полей блокируются
                  перед реальным запуском.
                </span>
              </div>
              <details>
                <summary>Настроить Contact Score</summary>
                <p className="muted">
                  Доля заполненных контактов с учётом весов. Собственный
                  показатель приложения.
                </p>
                <div className="form-grid">
                  {Object.entries(spec.score_weights).map(([k, v]) => (
                    <label key={k}>
                      {meta.fields[k]}
                      <input
                        type="number"
                        min="0"
                        value={v}
                        onChange={(e) =>
                          setSpec({
                            score_weights: {
                              ...spec.score_weights,
                              [k]: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                  ))}
                </div>
              </details>
            </>
          )}
          {step === 3 && (
            <>
              <div className="form-grid">
                <label>
                  Лимит организаций
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    value={spec.limit}
                    onChange={(e) => setSpec({ limit: Number(e.target.value) })}
                  />
                </label>
                <label>
                  Лимит запросов
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={spec.request_limit}
                    onChange={(e) =>
                      setSpec({ request_limit: Number(e.target.value) })
                    }
                  />
                </label>
                <label>
                  Запросов в секунду
                  <input
                    type="number"
                    min="0.1"
                    max="5"
                    step="0.1"
                    value={spec.requests_per_second}
                    onChange={(e) =>
                      setSpec({ requests_per_second: Number(e.target.value) })
                    }
                  />
                </label>
                <label>
                  Удалять дубликаты по
                  <select
                    value={spec.dedup}
                    onChange={(e) => setSpec({ dedup: e.target.value })}
                  >
                    {Object.entries({
                      branch_id: "ID филиала · сохранить филиалы",
                      org_id: "ID организации · одна запись",
                      phone: "Телефону",
                      website: "Домену сайта",
                      name_address: "Названию и адресу",
                    }).map(([k, v]) => (
                      <option value={k} key={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label>Колонки результата</label>
              <div className="column-checks">
                {Object.entries(meta.fields).map(([k, v]: any) => (
                  <label key={k}>
                    <input
                      type="checkbox"
                      checked={spec.columns.includes(k)}
                      onChange={() =>
                        setSpec({
                          columns: spec.columns.includes(k)
                            ? spec.columns.filter((x) => x !== k)
                            : [...spec.columns, k],
                        })
                      }
                    />
                    {v}
                    {meta.mode === "live" && !meta.capabilities.fields?.[k] && (
                      <span title="Доступ не подтверждён"> · ?</span>
                    )}
                  </label>
                ))}
              </div>
              <div className="help-box">
                <Info size={17} />
                <span>
                  Количество запросов зависит от страниц и рубрик. Максимум —{" "}
                  {spec.request_limit}. Частоту выбирайте в пределах лимитов
                  вашего договора.
                </span>
              </div>
            </>
          )}
          <div className="wizard-footer">
            <Button disabled={step === 0} onClick={() => setStep(step - 1)}>
              <ArrowLeft size={15} />
              Назад
            </Button>
            {step < 3 ? (
              <Button primary onClick={() => setStep(step + 1)}>
                Продолжить
                <ArrowRight size={16} />
              </Button>
            ) : (
              <Button
                primary
                disabled={
                  busy ||
                  !spec.cities.length ||
                  !spec.categories.length ||
                  !meta.capabilities.connected
                }
                onClick={() =>
                  run(async () => {
                    const j = await send("/jobs", { ...spec, mode: meta.mode });
                    onCreated(j.id);
                  })
                }
              >
                <Play size={16} />
                Начать поиск
              </Button>
            )}
          </div>
        </div>
        <div className="summary panel">
          <div className="summary-title">
            <Layers size={18} />
            <h3>Ваш поиск</h3>
          </div>
          <div>
            <small>ГЕОГРАФИЯ</small>
            <p>
              {spec.cities.map((c) => c.name).join(", ") ||
                "Города ещё не выбраны"}
            </p>
          </div>
          <div>
            <small>КАТЕГОРИИ</small>
            <p>{spec.categories.join(", ") || "Выберите сферы бизнеса"}</p>
          </div>
          <div>
            <small>УСЛОВИЯ</small>
            <p>
              {spec.filters.conditions.length} условий и групп ·{" "}
              {spec.filters.logic === "AND" ? "все" : "любое"}
            </p>
          </div>
          <div>
            <small>РЕЗУЛЬТАТ</small>
            <p>
              До {spec.limit.toLocaleString("ru-RU")} организаций
              <br />
              {spec.columns.length} колонок
            </p>
          </div>
          <div className="summary-foot">
            <Database size={16} />
            {meta.mode === "demo" ? "Тестовые данные" : "Официальный API 2ГИС"}
          </div>
        </div>
      </div>
    </>
  );
}
