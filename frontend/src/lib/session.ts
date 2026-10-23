/**
 * Which field the signed-in farmer is working in. For now every farmer has one field, "My field",
 * created on first use. Later (several fields) add a field picker and keep the chosen id here.
 */
import { api } from "@/lib/api";

let pending: Promise<number> | null = null;

/** Returns the id of the farmer's first field, creating it if the farmer has none yet. */
export function ensureField(): Promise<number> {
  pending ??= (async () => {
    const fields = await api.listFields();
    return fields.length ? fields[0].id : (await api.createField("My field")).id;
  })().finally(() => {
    pending = null;
  });
  return pending;
}
