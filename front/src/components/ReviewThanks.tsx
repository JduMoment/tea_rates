import { DONATE_URL } from '../donate'

/** «Спасибо» после нового отзыва; раз в месяц — с тихой просьбой поддержать проект. */
export function ReviewThanks({ askDonate, onClose }: { askDonate: boolean; onClose: () => void }) {
  return (
    <div className="review-thanks" role="status">
      <div className="stack" style={{ gap: 4 }}>
        <strong>Спасибо, отзыв опубликован!</strong>
        {askDonate && (
          <span>
            Сайт без рекламы и держится на энтузиазме. Если он полезен — можно{' '}
            <a href={DONATE_URL} target="_blank" rel="noopener noreferrer">
              угостить автора чаем ☕
            </a>
          </span>
        )}
      </div>
      <button type="button" className="btn btn-ghost btn-sm" aria-label="Закрыть" onClick={onClose}>
        ✕
      </button>
    </div>
  )
}
