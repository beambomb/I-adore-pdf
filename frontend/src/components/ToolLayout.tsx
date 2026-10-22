import type { ReactNode } from "react";

interface ToolLayoutProps {
  title: string;
  description: string;
  children: ReactNode;
}

export default function ToolLayout({ title, description, children }: ToolLayoutProps) {
  return (
    <section>
      <div className="page-intro">
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="panel">{children}</div>
    </section>
  );
}
