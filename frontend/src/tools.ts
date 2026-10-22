export interface ToolInfo {
  path: string;
  title: string;
  description: string;
}

/** Every implemented tool. Each task appends its own entry here. */
export const tools: ToolInfo[] = [];
