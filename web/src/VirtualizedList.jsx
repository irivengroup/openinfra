import React, { useMemo, useState } from 'react';
import { virtualWindow } from './core/virtual-window.js';

export function VirtualizedList({ items, renderItem, ariaLabel = 'Results', rowHeight = 44, viewportHeight = 384, overscan = 4 }) {
  const [scrollTop, setScrollTop] = useState(0);
  const range = useMemo(() => virtualWindow({ itemCount: items.length, scrollTop, viewportHeight, rowHeight, overscan }), [items.length, overscan, rowHeight, scrollTop, viewportHeight]);
  const visible = items.slice(range.start, range.end);
  return <div role="list" aria-label={ariaLabel} tabIndex="0" style={{ maxHeight: viewportHeight, overflowY: 'auto' }} onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}>
    <div aria-hidden="true" style={{ height: range.offsetTop }} />
    {visible.map((item, index) => <div role="listitem" aria-posinset={range.start + index + 1} aria-setsize={items.length} key={item.id || range.start + index} style={{ minHeight: rowHeight }}>{renderItem(item, range.start + index)}</div>)}
    <div aria-hidden="true" style={{ height: Math.max(0, range.totalHeight - range.offsetTop - visible.length * rowHeight) }} />
  </div>;
}
