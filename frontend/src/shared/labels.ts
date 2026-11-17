export function isDemo() {
  return process.env.DATA_MODE === "demo";
}

export function matchStatusLabel(status: string) {
  if (status === "scheduled") return "Запланирован";
  if (status === "live") return "Идёт";
  if (status === "finished") return "Завершён";
  if (status === "cancelled") return "Отменён";
  return status;
}

export function questionStatusLabel(status: string) {
  if (status === "open") return "Открыт";
  if (status === "closed") return "Закрыт";
  if (status === "withdrawn") return "Снят";
  return status;
}

export function outcomeLabel(outcome: string) {
  if (outcome === "home") return "Победа хозяев";
  if (outcome === "away") return "Победа гостей";
  if (outcome === "draw") return "Ничья";
  return outcome;
}

export function reasonLabel(reason: string) {
  if (reason === "sport") return "Совпадает с интересом";
  if (reason === "popularity") return "Часто открывают";
  if (reason === "content") return "Похоже на прочитанное";
  if (reason === "blend") return "Смешанная выдача";
  return reason;
}

export function errorMessage(status: number, detail: string, fallback: string) {
  if (status === 401) return "Сессия истекла. Войдите снова.";
  if (status === 403) return "Недостаточно прав для этого действия.";
  if (status === 404 && detail === "match not found") return "Копия матча в прогнозах ещё не появилась.";
  if (status === 409 && detail.toLowerCase().includes("closed")) return "Вопрос закрылся до отправки ответа.";
  if (detail && !detail.includes("Traceback") && detail.length < 240) return detail;
  return fallback;
}
