import { useCallback, useRef, useState } from "react";
import type { QueuedFile } from "../components/FileList";
import { moveItem, removeAt } from "../lib/reorder";

/** Ordered list of selected files with add, reorder and remove helpers. */
export function useFileQueue() {
  const nextId = useRef(1);
  const [items, setItems] = useState<QueuedFile[]>([]);

  const add = useCallback((files: File[]) => {
    setItems((current) => [...current, ...files.map((file) => ({ id: nextId.current++, file }))]);
  }, []);
  const move = useCallback(
    (from: number, to: number) => setItems((current) => moveItem(current, from, to)),
    [],
  );
  const remove = useCallback(
    (index: number) => setItems((current) => removeAt(current, index)),
    [],
  );
  const clear = useCallback(() => setItems([]), []);

  return { items, add, move, remove, clear };
}
