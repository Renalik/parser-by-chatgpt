import React, { useEffect, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import {
  House,
  Search,
  Tags,
  SlidersHorizontal,
  Table2,
  Download,
  History,
  Settings,
  Plus,
  ArrowRight,
  MapPin,
  Check,
  ChevronRight,
  X,
  Trash2,
  KeyRound,
  Globe,
  Info,
  FileDown,
  Layers,
  Building2,
} from "lucide-react";

import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "./style.css";
import { api, send } from "./api";
import { useStore } from "./store";
import { Button, Empty, status, date } from "./components/ui";
import JobList from "./components/JobList";
import SearchWizard from "./components/SearchWizard";
import Results from "./components/Results";
import Exporter from "./components/Exporter";
import SettingsPage from "./components/SettingsPage";
const nav = [
  ["Главная", House],
  ["Новый поиск", Search],
  ["Категории", Tags],
  ["Фильтры", SlidersHorizontal],
  ["Результаты", Table2],
  ["Экспорт", Download],
  ["История", History],
  ["Настройки", Settings],
] as const;
function App() {
  const { page, setPage, spec, setSpec, jobId, setJob } = useStore();
  const [meta, setMeta] = useState<any>(null),
    [jobs, setJobs] = useState<any[]>([]),
    [templates, setTemplates] = useState<any[]>([]),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    const [m, j, t] = await Promise.all([
      api("/meta"),
      api("/jobs"),
      api("/templates"),
    ]);
    setMeta(m);
    setJobs(j);
    setTemplates(t);
  }, []);
  useEffect(() => {
    refresh().catch((e) => setNotice(e.message));
    const timer = setInterval(() => {
      api("/jobs")
        .then(setJobs)
        .catch(() => {});
      api("/meta")
        .then(setMeta)
        .catch(() => {});
    }, 1500);
    return () => clearInterval(timer);
  }, [refresh]);
  const run = async (fn: () => Promise<any>) => {
    setBusy(true);
    try {
      await fn();
      await refresh();
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setBusy(false);
    }
  };
  const newSearch = () => {
    setPage("Новый поиск");
    setSpec({ mode: meta?.mode || "live" });
  };
  if (!meta)
    return <div className="loading">{notice || "Загрузка приложения…"}</div>;
  const active = jobs.find((j) => j.id === jobId) || jobs[0];
  const open = (id: string) => {
    setJob(id);
    setPage("Результаты");
  };
  const saveTemplate = () =>
    run(async () => {
      const name = window.prompt("Название шаблона", spec.name);
      if (name)
        await send("/templates", {
          name,
          kind: "search",
          value: { ...spec, mode: meta.mode },
        });
    });
  return (
    <div className="app">
      <aside>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("Главная");
          }}
        >
          <span className="brand-symbol">
            <Layers size={23} />
          </span>
          <div>
            2GIS<span>BUSINESS PARSER</span>
          </div>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">Л</span>
          <div>
            Личное пространство<small>Рабочая область</small>
          </div>
        </div>
        <div className="nav-label">ПРОСТРАНСТВО</div>
        <nav>
          {nav.map(([name, Icon]) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              onClick={() => setPage(name)}
            >
              <Icon size={18} />
              {name}
              {name === "История" && (
                <span className="count">{jobs.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="source-icon">
            <Globe size={18} />
          </div>
          <div>
            <b>
              {meta.mode === "demo"
                ? "Деморежим"
                : meta.mode === "browser"
                  ? "2ГИС · браузер"
                  : "Источник: 2ГИС"}
            </b>
            <small>
              {meta.capabilities.connected
                ? "Подключение активно"
                : "Требуется подключение"}
            </small>
          </div>
          <button
            aria-label="Настроить источник"
            onClick={() => setPage("Настройки")}
          >
            <ChevronRight size={16} />
          </button>
        </div>
        <div className="version">
          Business Parser <span>v1.0</span>
        </div>
      </aside>
      <div className="main">
        <header>
          <div className="breadcrumb">
            Рабочая область <ChevronRight size={14} />
            <b>{page}</b>
          </div>
          <div className="header-right">
            <span className="connection">
              <i className={meta.capabilities.connected ? "connected" : ""} />
              {meta.mode === "demo"
                ? "Демо · тестовые данные"
                : meta.mode === "browser"
                  ? meta.capabilities.connected
                    ? "Браузер готов"
                    : "Браузер не найден"
                  : meta.capabilities.connected
                    ? "API подключён"
                    : "API не подключён"}
            </span>
            <button
              className="avatar"
              aria-label="Настройки"
              onClick={() => setPage("Настройки")}
            >
              Л
            </button>
          </div>
        </header>
        <main>
          {meta.mode === "demo" && (
            <div className="demo-banner">
              <Info size={16} />
              Демонстрационный режим. Все организации — вымышленные примеры.
              <button onClick={() => setPage("Настройки")}>
                Выбрать источник <ArrowRight size={14} />
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="alert">
              <Info size={18} />
              <span>{notice}</span>
              <button
                aria-label="Закрыть уведомление"
                onClick={() => setNotice("")}
              >
                <X size={18} />
              </button>
            </div>
          )}
          {page === "Главная" && (
            <>
              <div className="page-heading">
                <div className="eyebrow">ВАШ РАБОЧИЙ ОБЗОР</div>
                <div className="heading-row">
                  <div>
                    <h1>
                      Бизнес начинается с поиска
                      <span className="period">.</span>
                    </h1>
                    <p>
                      Находите организации. Отбирайте нужное. Работайте с
                      данными.
                    </p>
                  </div>
                  <Button primary onClick={newSearch}>
                    <Plus size={17} />
                    Новый поиск
                  </Button>
                </div>
              </div>
              <div className="stats">
                {[
                  ["Всего задач", jobs.length, Layers],
                  [
                    "Обработано организаций",
                    jobs.reduce((a, j) => a + j.processed, 0),
                    Building2,
                  ],
                  [
                    "Подходящих организаций",
                    jobs.reduce((a, j) => a + j.matched, 0),
                    Check,
                  ],
                  [
                    "Последний поиск",
                    jobs[0] ? date(jobs[0].created_at) : "Ещё не запускали",
                    History,
                  ],
                ].map(([label, value, Icon]: any, i) => (
                  <div className="stat" key={label}>
                    <div className="stat-label">
                      {label}
                      <Icon size={17} />
                    </div>
                    <div className={"stat-value " + (i === 3 ? "small" : "")}>
                      {typeof value === "number"
                        ? value.toLocaleString("ru-RU")
                        : value}
                    </div>
                    <small>
                      {
                        [
                          "В вашей рабочей области",
                          "Во всех поисковых задачах",
                          "После применения фильтров",
                          "История сохраняется автоматически",
                        ][i]
                      }
                    </small>
                  </div>
                ))}
              </div>
              {!meta.capabilities.connected && (
                <div className="connect-card">
                  <div className="connect-icon">
                    <KeyRound size={24} />
                  </div>
                  <div>
                    <h3>Выберите источник и начните поиск.</h3>
                    <p>
                      Добавьте ключ 2ГИС или познакомьтесь с приложением на
                      тестовых данных.
                    </p>
                  </div>
                  <Button onClick={() => setPage("Настройки")}>
                    Настроить подключение
                    <ArrowRight size={16} />
                  </Button>
                </div>
              )}
              <div className="section-heading">
                <div>
                  <h2>
                    Последние задачи <span className="tag">{jobs.length}</span>
                  </h2>
                  <p>Все ваши поиски и их результаты в одном месте</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => setPage("История")}
                >
                  Вся история <ArrowRight size={16} />
                </button>
              </div>
              {jobs.length ? (
                <JobList
                  jobs={jobs.slice(0, 5)}
                  open={open}
                  run={run}
                  onRepeat={(j: any) => {
                    setSpec(j.spec);
                    newSearch();
                  }}
                />
              ) : (
                <Empty
                  title="Начните с первого поиска"
                  text="Выберите город, категории бизнеса и нужные контакты."
                >
                  <Button primary onClick={newSearch}>
                    <Plus size={16} />
                    Создать поиск
                  </Button>
                </Empty>
              )}
              <div className="steps-overview">
                {[
                  [
                    MapPin,
                    "01",
                    "Задайте географию",
                    "Один город или несколько регионов",
                  ],
                  [
                    SlidersHorizontal,
                    "02",
                    "Отберите подходящее",
                    "Категории, контакты и точные фильтры",
                  ],
                  [
                    FileDown,
                    "03",
                    "Получите результат",
                    "Ваши колонки в CSV, Excel или JSON",
                  ],
                ].map(([Icon, n, t, d]: any) => (
                  <div key={n}>
                    <div className="step-icon">
                      <Icon size={19} />
                    </div>
                    <span>{n}</span>
                    <h3>{t}</h3>
                    <p>{d}</p>
                  </div>
                ))}
              </div>
            </>
          )}
          {["Новый поиск", "Категории", "Фильтры"].includes(page) && (
            <SearchWizard
              meta={meta}
              run={run}
              busy={busy}
              onCreated={open}
              saveTemplate={saveTemplate}
              templates={templates}
              standalone={page}
            />
          )}
          {(page === "Результаты" || page === "Экспорт") && (
            <>
              <div className="page-heading">
                <div className="eyebrow">ДАННЫЕ ОРГАНИЗАЦИЙ</div>
                <h1>{page}</h1>
                <p>Только нужная информация, в удобном для вас виде.</p>
              </div>
              {!active ? (
                <Empty
                  title="Пока нет результатов"
                  text="Создайте поисковую задачу, чтобы начать работу с организациями."
                >
                  <Button primary onClick={newSearch}>
                    Новый поиск
                    <ArrowRight size={16} />
                  </Button>
                </Empty>
              ) : (
                <>
                  <div className="job-select">
                    <label>
                      Поисковая задача
                      <select
                        value={active.id}
                        onChange={(e) => setJob(e.target.value)}
                      >
                        {jobs.map((j) => (
                          <option key={j.id} value={j.id}>
                            {j.name} · {date(j.created_at)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <span className="tag">{status[active.status]}</span>
                  </div>
                  {page === "Результаты" ? (
                    <Results
                      job={active}
                      meta={meta}
                      run={run}
                      toExport={() => setPage("Экспорт")}
                    />
                  ) : (
                    <Exporter
                      job={active}
                      meta={meta}
                      run={run}
                      templates={templates}
                    />
                  )}
                </>
              )}
            </>
          )}
          {page === "История" && (
            <>
              <div className="page-heading">
                <div className="heading-row">
                  <div>
                    <h1>История поиска</h1>
                    <p>
                      Возвращайтесь к результатам и повторяйте удачные поиски.
                    </p>
                  </div>
                  <Button primary onClick={newSearch}>
                    <Plus size={16} />
                    Новый поиск
                  </Button>
                </div>
              </div>
              {jobs.length ? (
                <JobList
                  jobs={jobs}
                  open={open}
                  run={run}
                  onRepeat={(j: any) => {
                    setSpec({ ...j.spec, name: j.name + " · копия" });
                    newSearch();
                  }}
                />
              ) : (
                <Empty
                  title="История пока пуста"
                  text="Здесь появятся ваши поисковые задачи."
                />
              )}
              <h2 className="mt">Сохранённые шаблоны</h2>
              <div className="template-grid">
                {templates
                  .filter((t) => t.kind === "search")
                  .map((t) => (
                    <div className="panel" key={t.id}>
                      <h3>{t.name}</h3>
                      <p>
                        {t.value.cities.map((c: any) => c.name).join(", ")} ·{" "}
                        {t.value.categories.length} категорий
                      </p>
                      <Button
                        onClick={() => {
                          setSpec(t.value);
                          newSearch();
                        }}
                      >
                        Применить
                        <ArrowRight size={15} />
                      </Button>
                      <Button
                        aria-label="Удалить шаблон"
                        onClick={() =>
                          run(() =>
                            api("/templates/" + t.id, { method: "DELETE" }),
                          )
                        }
                      >
                        <Trash2 size={15} />
                      </Button>
                    </div>
                  ))}
              </div>
              {!templates.length && (
                <p className="muted">Сохраните настройки в мастере поиска.</p>
              )}
            </>
          )}
          {page === "Настройки" && (
            <SettingsPage meta={meta} run={run} busy={busy} />
          )}
          <footer>
            <span>2GIS Business Parser</span>
            <span>Данные с ясной целью.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
