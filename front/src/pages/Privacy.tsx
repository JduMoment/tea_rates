import { usePageTitle } from '../hooks/usePageTitle'
import { PageHero } from '../components/PageHero'
import { choose } from '../components/CookieBanner'
import { setConsent, useConsent } from '../consent'

const OPERATOR = 'Курагин Иван Фёдорович'
const CONTACT_EMAIL = 'admin@5listov.ru'
const UPDATED = '10 ноября 2026'

/** Политика конфиденциальности и управление согласием на cookie. */
export function Privacy() {
  usePageTitle('Политика конфиденциальности')
  const consent = useConsent()

  return (
    <div className="page">
      <PageHero eyebrow={`Обновлено ${UPDATED}`} title="Конфиденциальность" lead="Какие данные собирает сайт «5 листов», зачем и как от этого отказаться." />

      <article className="card prose">
        <h2>Кто обрабатывает данные</h2>
        <p>
          Оператор персональных данных — {OPERATOR}. Вопросы, запросы на удаление и отзыв согласия:{' '}
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
        </p>

        <h2>Какие данные мы храним</h2>
        <ul>
          <li>
            <b>Аккаунт:</b> имя, адрес почты и пароль (в зашифрованном виде, сам пароль мы не знаем). При входе через
            Яндекс ID — ещё идентификатор Яндекса, почта и имя из него.
          </li>
          <li>
            <b>Что вы публикуете:</b> отзывы, оценки, фото, магазины и чаи. Отзывы и профиль видны всем посетителям.
          </li>
          <li>
            <b>Дневник и полка</b> — видны только вам.
          </li>
          <li>
            <b>Обратная связь:</b> текст сообщения, почта (если указали), адрес страницы, браузер и IP-адрес — IP нужен,
            чтобы отсекать спам.
          </li>
        </ul>
        <p>Данные хранятся на сервере в России и не передаются третьим лицам, кроме случаев, описанных ниже.</p>

        <h2>Cookie</h2>
        <ul>
          <li>
            <b>Необходимые</b> — cookie сессии: без неё нельзя войти на сайт. Ставится, только когда вы входите.
          </li>
          <li>
            <b>Аналитика</b> — Яндекс Метрика (ООО «Яндекс»): считает посещения, откуда пришли посетители и какие страницы
            смотрят. Подключается, только если вы нажали «Принять». Данные обрабатываются обезличенно, по{' '}
            <a href="https://yandex.ru/legal/metrica_termsofuse/" target="_blank" rel="noreferrer">
              условиям Яндекса
            </a>
            .
          </li>
        </ul>
        <p>
          Сейчас: <b>{consent === 'all' ? 'аналитика разрешена' : consent === 'necessary' ? 'только необходимые' : 'выбор не сделан'}</b>.
        </p>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          {consent !== 'all' && (
            <button type="button" className="btn btn-sm" onClick={() => choose('all')}>
              Разрешить аналитику
            </button>
          )}
          {consent !== 'necessary' && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => choose('necessary')}>
              Только необходимые
            </button>
          )}
          {consent && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConsent(null)}>
              Спросить заново
            </button>
          )}
        </div>

        <h2>Сколько храним и как удалить</h2>
        <p>
          Данные аккаунта хранятся, пока аккаунт существует. Напишите на{' '}
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> — удалим аккаунт вместе с отзывами, дневником и
          фото в течение 30 дней. Также можно запросить, какие данные о вас хранятся, или исправить их.
        </p>

        <h2>Согласие</h2>
        <p>
          Регистрируясь, вы соглашаетесь на обработку перечисленных данных для работы сайта. Согласие можно отозвать в
          любой момент, написав нам, — тогда аккаунт будет удалён.
        </p>
      </article>
    </div>
  )
}
