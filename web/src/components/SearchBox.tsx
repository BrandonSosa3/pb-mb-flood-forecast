import { useEffect, useId, useState } from "react";
import { type Hit, type SearchIndex, loadSearch, search } from "../search";

/** Search box with a suggestion list. Picking a result opens the map at that spot. */
export function SearchBox() {
  const listId = useId();
  const [ix, setIx] = useState<SearchIndex | null>(null);
  const [failed, setFailed] = useState(false);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const prepare = () => {
    if (!ix) loadSearch().then(setIx).catch(() => setFailed(true));
  };
  const hits: Hit[] = ix && q.trim() ? search(ix, q) : [];
  useEffect(() => setActive(0), [q]);

  const go = (h: Hit) => {
    setOpen(false);
    window.location.hash = `#/map?spot=${h.key}`;
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!hits.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => (a + 1) % hits.length); setOpen(true); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => (a - 1 + hits.length) % hits.length); }
    else if (e.key === "Enter") { e.preventDefault(); go(hits[active]); }
    else if (e.key === "Escape") setOpen(false);
  };

  const showList = open && q.trim().length > 0;
  return (
    <div className="searchbox">
      <div className="search">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4F5D6B" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
        </svg>
        <label htmlFor="search" className="visually-hidden">Search a street, address or place</label>
        <input id="search" type="search" placeholder="Search a street or address" autoComplete="off"
          role="combobox" aria-expanded={showList} aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={showList && hits.length ? `${listId}-${active}` : undefined}
          value={q} onFocus={() => { prepare(); setOpen(true); }} onKeyDown={onKey}
          onChange={(e) => { setQ(e.target.value); setOpen(true); prepare(); }}
          onBlur={() => setTimeout(() => setOpen(false), 150)} />
      </div>
      {showList && (
        <ul id={listId} role="listbox" className="suggest" aria-label="Search results">
          {failed ? <li className="suggest-empty">Search isn't available right now.</li>
            : !ix ? <li className="suggest-empty">Loading…</li>
            : hits.length === 0 ? <li className="suggest-empty">No match in Pacific Beach, Mission Beach or Crown Point.</li>
            : hits.map((h, i) => (
              <li key={h.key} id={`${listId}-${i}`} role="option" aria-selected={i === active}
                onMouseDown={(e) => e.preventDefault()} onClick={() => go(h)} onMouseEnter={() => setActive(i)}>
                <span className="row-title">{h.title}</span>
                <span className="row-sub">{h.sub}</span>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
