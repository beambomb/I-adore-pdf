/** Return a copy of `items` with the element at `from` moved to `to`. Out-of-range moves are ignored. */
export function moveItem<T>(items: readonly T[], from: number, to: number): T[] {
  const copy = [...items];
  if (from < 0 || from >= copy.length || to < 0 || to >= copy.length || from === to) {
    return copy;
  }
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}

export function removeAt<T>(items: readonly T[], index: number): T[] {
  return items.filter((_, i) => i !== index);
}
