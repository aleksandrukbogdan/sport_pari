import { EmptyState, ErrorState, PageTitle, SkeletonBlock, StatusBadge } from "@/shared/ui";

export default function ComponentsPage() {
  return (
    <div className="stack">
      <PageTitle title="Компоненты">
        <p className="muted">Общие состояния интерфейса sport_pari.</p>
      </PageTitle>
      <section className="row">
        <button className="button primary" type="button">Основное действие</button>
        <button className="button secondary" type="button">Вторичное</button>
        <button className="button danger" type="button">Опасное</button>
        <button className="button primary" type="button" disabled>Недоступно</button>
      </section>
      <section className="row">
        <StatusBadge status="open" label="Открыт" />
        <StatusBadge status="closed" label="Закрыт" />
        <StatusBadge status="withdrawn" label="Снят" />
        <StatusBadge status="scheduled" label="Запланирован" />
        <StatusBadge status="live" label="Идёт" />
        <StatusBadge status="finished" label="Завершён" />
      </section>
      <form className="stack surface">
        <label className="field"><span>Поле</span><input placeholder="Текст" /></label>
        <label className="field"><span>Список</span><select><option>Вариант</option></select></label>
        <label className="field"><span>Комментарий</span><textarea defaultValue="Короткий текст" /></label>
        <label className="check"><input type="checkbox" defaultChecked /><span>Флажок</span></label>
        <label className="check"><input type="radio" name="sample" defaultChecked /><span>Да</span></label>
        <label className="check"><input type="radio" name="sample" /><span>Нет</span></label>
      </form>
      <SkeletonBlock />
      <EmptyState title="Пустой список" text="Пока нечего показать." />
      <ErrorState message="Не удалось загрузить матчи. Попробуйте ещё раз." href="/components" />
    </div>
  );
}
