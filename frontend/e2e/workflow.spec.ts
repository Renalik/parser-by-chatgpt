import { test, expect } from "@playwright/test";
test("Подключение демо, мастер, таблица, экспорт и адаптивность", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Бизнес начинается с поиска." }),
  ).toBeVisible();
  await page.screenshot({ path: "/tmp/parser-dashboard.png", fullPage: true });
  await page.locator("nav").getByRole("button", { name: "Настройки" }).click();
  await page.getByRole("button", { name: "Открыть деморежим" }).click();
  await expect(page.getByText("Демо · тестовые данные")).toBeVisible();
  await page
    .locator("nav")
    .getByRole("button", { name: "Новый поиск" })
    .click();
  await page.getByLabel("Название задачи").fill("Проверка браузера");
  await page.getByPlaceholder("Например, Москва").fill("Москва");
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  await page
    .locator(".suggestions")
    .getByRole("button", { name: "Москва" })
    .click();
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page.getByLabel("Кофейни", { exact: true }).check();
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page.getByRole("button", { name: "Условие", exact: true }).click();
  await page.getByLabel("Поле фильтра").selectOption("phone");
  await page.getByLabel("Условие", { exact: true }).selectOption("present");
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page.getByLabel("Лимит организаций").fill("10");
  await page.getByRole("button", { name: "Начать поиск" }).click();
  await expect(page.getByText("10 подходит", { exact: false })).toBeVisible({
    timeout: 15000,
  });
  await expect(page.locator(".result-table tbody tr")).toHaveCount(10);
  await page
    .locator(".result-table")
    .getByRole("button")
    .filter({ hasText: "пример" })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Закрыть карточку" }).click();
  await page
    .getByRole("button", { name: "Экспорт", exact: true })
    .last()
    .click();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Скачать XLSX" }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  await page.locator("nav").getByRole("button", { name: "Главная" }).click();
  await page.screenshot({
    path: "/tmp/parser-dashboard-data.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.screenshot({ path: "/tmp/parser-tablet.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
