export function virtualWindow({ itemCount, scrollTop = 0, viewportHeight = 360, rowHeight = 44, overscan = 4 }) {
  const count = Math.max(0, Number(itemCount) || 0);
  const height = Math.max(1, Number(rowHeight) || 44);
  const viewport = Math.max(height, Number(viewportHeight) || 360);
  const first = Math.floor(Math.max(0, scrollTop) / height);
  const start = Math.max(0, first - overscan);
  const end = Math.min(count, first + Math.ceil(viewport / height) + overscan);
  return { start, end, offsetTop: start * height, totalHeight: count * height };
}
