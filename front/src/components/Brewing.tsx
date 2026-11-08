import { Link } from 'react-router'
import type { Brewed, Brewing } from '../data/types'
import { plural } from '../utils/format'

const num = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1).replace('.', ','))
const range = ([a, b]: [number, number]) => (a === b ? num(a) : `${num(a)}–${num(b)}`)

function Tiles({ items }: { items: { label: string; value: string }[] }) {
  return (
    <div className="brew-tiles">
      {items.map((it) => (
        <div key={it.label} className="brew-tile">
          <span className="brew-value">{it.value}</span>
          <span className="small muted">{it.label}</span>
        </div>
      ))}
    </div>
  )
}

function brewedTiles(b: Brewed) {
  return [
    { label: 'вода', value: `${b.water} °C` },
    b.gramsPer100 != null
      ? { label: 'на 100 мл воды', value: `${num(b.gramsPer100)} г` }
      : { label: 'заварки', value: `${num(b.grams)} г` },
    { label: plural(b.infusions, 'пролив', 'пролива', 'проливов'), value: String(b.infusions) },
    ...(b.volume ? [{ label: 'объём посуды', value: `${b.volume} мл` }] : []),
  ]
}

/** «Как заваривают этот чай». */
export function BrewingBlock({ teaId, brewing }: { teaId: number; brewing: Brewing }) {
  const { community, liked, typical } = brewing
  const differs =
    liked && community && (liked.water !== community.water || liked.infusions !== community.infusions || liked.gramsPer100 !== community.gramsPer100)
  return (
    <section className="card stack" aria-labelledby="brew-h">
      <div className="section-head" style={{ margin: 0 }}>
        <h2 id="brew-h">Как заваривают</h2>
        <Link to={`/diary?add=${teaId}`} className="small" style={{ fontWeight: 700 }}>Записать своё чаепитие →</Link>
      </div>
      {community ? (
        <>
          <p className="small muted" style={{ margin: 0 }}>
            Медиана по {community.entries} {plural(community.entries, 'записи', 'записям', 'записям')} в дневниках{' '}
            {community.people} {plural(community.people, 'человека', 'человек', 'человек')}.
          </p>
          <Tiles items={brewedTiles(community)} />
          {differs && liked && (
            <>
              <p className="small" style={{ margin: 0, fontWeight: 700 }}>Те, кому понравилось (4–5 листиков):</p>
              <Tiles items={brewedTiles(liked)} />
            </>
          )}
        </>
      ) : (
        <>
          <p className="small muted" style={{ margin: 0 }}>
            Записей в дневниках пока мало — вот как обычно заваривают {brewing.category.toLowerCase()}:
          </p>
          <Tiles
            items={[
              { label: 'вода', value: `${range(typical.water)} °C` },
              { label: 'на 100 мл воды', value: `${range(typical.gramsPer100)} г` },
              { label: 'проливов', value: range(typical.infusions) },
            ]}
          />
        </>
      )}
    </section>
  )
}
