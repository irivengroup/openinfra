export function virtualWindow({ itemCount, scrollTop = 0, viewportHeight = 360, rowHeight = 44, overscan = 4 }) {
  const safeCount = Math.max(0, Number(itemCount) || 0);
  const safeRowHeight = Math.max(1, Number(rowHeight) || 44);
  const safeViewport = Math.max(safeRowHeight, Number(viewportHeight) || 360);
  const firstVisible = Math.floor(Math.max(0, scrollTop) / safeRowHeight);
  const visibleCount = Math.ceil(safeViewport / safeRowHeight);
  const start = Math.max(0, firstVisible - overscan);
  const end = Math.min(safeCount, firstVisible + visibleCount + overscan);
  return { start, end, offsetTop: start * safeRowHeight, totalHeight: safeCount * safeRowHeight };
}

export class OpenInfraVirtualList {
  constructor(container, { items, renderItem, rowHeight = 44, overscan = 4, ariaLabel = "Résultats" }) {
    this.container = container;
    this.items = Array.isArray(items) ? items : [];
    this.renderItem = renderItem;
    this.rowHeight = rowHeight;
    this.overscan = overscan;
    this.ariaLabel = ariaLabel;
    this.onScroll = () => this.render();
  }

  mount() {
    this.container.setAttribute("role", "list");
    this.container.setAttribute("aria-label", this.ariaLabel);
    this.container.style.overflowY = "auto";
    this.container.style.maxHeight = "24rem";
    this.container.addEventListener("scroll", this.onScroll, { passive: true });
    this.render();
    return this;
  }

  render() {
    const viewportHeight = this.container.clientHeight || 384;
    const range = virtualWindow({ itemCount: this.items.length, scrollTop: this.container.scrollTop, viewportHeight, rowHeight: this.rowHeight, overscan: this.overscan });
    const rows = this.items.slice(range.start, range.end).map((item, index) => {
      const absoluteIndex = range.start + index;
      return `<div role="listitem" aria-posinset="${absoluteIndex + 1}" aria-setsize="${this.items.length}" style="min-height:${this.rowHeight}px">${this.renderItem(item, absoluteIndex)}</div>`;
    }).join("");
    this.container.innerHTML = `<div aria-hidden="true" style="height:${range.offsetTop}px"></div>${rows}<div aria-hidden="true" style="height:${Math.max(0, range.totalHeight - range.offsetTop - (range.end - range.start) * this.rowHeight)}px"></div>`;
  }

  destroy() {
    this.container.removeEventListener("scroll", this.onScroll);
  }
}
